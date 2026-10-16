"""Verify version-3-only DIM loading, asset insertion and atomic saving."""
import hashlib
from pathlib import Path
import pickle
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from engine.dim_format import MAGIC, HEADER, CONTAINER_VERSION, DimFormatError, read_payload, write_payload


def envelope(payload, version=3, container=CONTAINER_VERSION):
    return MAGIC+HEADER.pack(container,version,len(payload),hashlib.sha256(payload).digest())+payload


def expect_error(function, error=Exception):
    try:
        function()
    except error:
        return
    raise AssertionError('Unsupported input was accepted')


def main():
    from PySide2.QtWidgets import QApplication
    app=QApplication([])
    from engine import core, model_files, serialization as codec
    core.CModel.InitSystem()
    with tempfile.TemporaryDirectory(prefix='deepdraw-dim-v3-') as temp:
        path=Path(temp)/'test.dim'
        model=core.CModel()
        try:
            original_top=model.GetTopComponent().GetID()
            payload=pickle.dumps(None,protocol=4)
            cases={str(version):envelope(payload,version) for version in (0,1,2,4,65535)}
            cases.update(empty=b'', headerless=payload, partial=MAGIC[:5],
                         truncated=MAGIC+b'\x01', container=envelope(payload,container=2),
                         checksum=envelope(payload)[:-1]+b'x', length=envelope(payload)+b'x')
            for name,data in cases.items():
                path.write_bytes(data)
                expect_error(lambda: read_payload(path),DimFormatError)
                for reader in (model_files.load_sketchup_model,model_files.load_sketchup_model_as_component):
                    expect_error(lambda: reader(model,str(path)),DimFormatError)
                assert model.GetTopComponent().GetID()==original_top,name
                assert model.getNumDefinition()==0,name
            # Even a v3 envelope cannot disguise a v2/missing/unknown model record.
            class Record:
                def __init__(self,version):self.version=version
                def __reduce__(self):
                    return codec.load_CModel,({'version':self.version,'materials':[],
                        'definitions':[],'top_component':{}},)
            for version in (None,0,1,2,4,'3',True):
                path.write_bytes(envelope(pickle.dumps(Record(version),protocol=4)))
                for reader in (model_files.load_sketchup_model,model_files.load_sketchup_model_as_component):
                    expect_error(lambda: reader(model,str(path)),ValueError)
            path.write_bytes(envelope(b'cbinary_file_v2\nload_CModel\n.'))
            for reader in (model_files.load_sketchup_model,model_files.load_sketchup_model_as_component):
                expect_error(lambda: reader(model,str(path)),pickle.UnpicklingError)
            # Version 3 output still round-trips through both public entry points.
            model_files.load_sketchup_model(model,str(ROOT/'data/ren.dim'))
            model_files.save_sketchup_model(model,str(path))
            version,stream=read_payload(path)
            stream.close()
            assert version==3
            asset=model_files.load_sketchup_model_as_component(model,str(path))
            assert list(asset.EnumEntities())
            original=path.read_bytes()
            def failed_writer(stream):
                stream.write(b'incomplete')
                raise RuntimeError('simulated writer failure')
            expect_error(lambda: write_payload(path,failed_writer),RuntimeError)
            assert path.read_bytes()==original
            expect_error(lambda: write_payload(path,lambda stream: None,payload_version=2),TypeError)
            assert path.read_bytes()==original
        finally:
            model.Release()
    assert 'engine.legacy_dim' not in sys.modules
    print('PASS: v3 model/asset round trip; other versions and corrupt files rejected; atomic failure preserves output')


if __name__=='__main__':
    main()
