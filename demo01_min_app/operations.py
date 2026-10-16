import core
#import utils

#+++++++++++++++++++++++
# OP:
# 删除选择的对象
#+++++++++++++++++++++++
def op_delete_selected(model):
    model.UndoManager().StartOperation("Delete select")
    
    selection = model.GetSelection()
    
    face_ls = []
    other_ls = []
    for e in selection:
        if type(e) is core.CFace:
            face_ls.append(e)
        else:
            other_ls.append(e)

    for e in face_ls:
        comp = e.GetParentComponent()
        assert comp
        e.Erase(comp)
    
    for e in other_ls:
        # check already delte
        if e.HasDeleted():
            print(f"{e} has delete, skip")
        else:
            comp = e.GetParentComponent()
            assert comp
            e.Erase(comp)
    
    model.UndoManager().CommitOperation()
    
    model.ClearSelection()



#+++++++++++++++++++++++
# OP:
# delete_all_guide_lines
#+++++++++++++++++++++++
def op_delete_all_guide_lines(model):
    model.UndoManager().StartOperation("Clear guide lines")
    
    comp = model.GetActiveComponent()
    
    guide_ls = []
    for e in comp.EnumEntities():
        if type(e) is core.CGuideLine:
            guide_ls.append(e)
    
    for e in guide_ls:
        comp = e.GetParentComponent()
        assert comp
        e.Erase(comp)
    
    model.UndoManager().CommitOperation()
    
    model.ClearSelection()
