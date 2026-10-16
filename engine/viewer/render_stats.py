"""Opt-in per-view CPU timings and native VBO submissions; no background sampling."""
from time import perf_counter
from .render_backend import native

class RenderStats:
    def __init__(self):
        self.active=False
        self.reset()
    def reset(self):
        self.sums={};self.maxima={};self.frames=0;self.since=perf_counter()
    def begin(self):
        self.phases={}
        self.current_stage='other';self.previous=(0,0,0)
        native.begin_statistics()
        self.active=True;self.started=perf_counter()
    def stage(self,name):
        current=native.statistics_snapshot()
        for key,value,previous in zip(('calls','triangles','lines'),current,self.previous):
            label=self.current_stage+'_'+key
            self.phases[label]=self.phases.get(label,0)+value-previous
        self.previous=current;self.current_stage=name
    def end(self,pipeline):
        elapsed=(perf_counter()-self.started)*1000
        self.stage('other')
        values=native.end_statistics();self.active=False
        values.update(self.phases);values['total']=elapsed
        timings=getattr(pipeline,'cache_timings',{})
        for key in ('enumerate_ms','tree_ms','context_ms','cull_ms','geometry_ms'):
            values[key]=timings.get(key,0)
        scene=getattr(pipeline,'_world_scene',None)
        if scene is not None:
            stats=scene.native.statistics()
            values.update(nodes=stats['nodes'],visible=stats['visible_nodes'],plane_tests=stats['plane_tests'])
            values['size_rejected']=stats.get('size_rejected',0)
        for key,value in values.items():
            self.sums[key]=self.sums.get(key,0)+value
            self.maxima[key]=max(self.maxima.get(key,0),value)
        self.frames+=1
    def take(self):
        if not self.frames:return None
        result=({k:v/self.frames for k,v in self.sums.items()},self.maxima,
                self.frames/(perf_counter()-self.since),self.frames)
        self.reset();return result
