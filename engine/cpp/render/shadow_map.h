// Private implementation included after DrawList. GL resources are context-owned.
// The bundled GLAD loader targets GL 2.0. Load the optional core/ARB FBO entry
// points explicitly per context; shadow-disabled rendering keeps its old minimum.
constexpr GLenum GL_FRAMEBUFFER=0x8D40, GL_DRAW_FRAMEBUFFER=0x8CA9, GL_READ_FRAMEBUFFER=0x8CA8;
constexpr GLenum GL_DRAW_FRAMEBUFFER_BINDING=0x8CA6, GL_READ_FRAMEBUFFER_BINDING=0x8CAA;
constexpr GLenum GL_DEPTH_ATTACHMENT=0x8D00, GL_FRAMEBUFFER_COMPLETE=0x8CD5;
using GenFramebuffer=void(APIENTRY*)(GLsizei,GLuint*);
using DeleteFramebuffer=void(APIENTRY*)(GLsizei,const GLuint*);
using BindFramebuffer=void(APIENTRY*)(GLenum,GLuint);
using AttachFramebuffer=void(APIENTRY*)(GLenum,GLenum,GLenum,GLuint,GLint);
using CheckFramebuffer=GLenum(APIENTRY*)(GLenum);
GenFramebuffer glGenFramebuffers=nullptr;
DeleteFramebuffer glDeleteFramebuffers=nullptr;
BindFramebuffer glBindFramebuffer=nullptr;
AttachFramebuffer glFramebufferTexture2D=nullptr;
CheckFramebuffer glCheckFramebufferStatus=nullptr;
template<class T>T shadow_proc(const char* name) {
    auto p=wglGetProcAddress(name);auto address=reinterpret_cast<intptr_t>(p);
    if(!p || address==1 || address==2 || address==3 || address==-1)
        throw std::runtime_error(std::string("Shadows require framebuffer support: ")+name);
    return reinterpret_cast<T>(p);
}
HGLRC shadow_gl_context=nullptr;
void load_shadow_gl() {
    auto context=current_context();if(shadow_gl_context==context) return;
    glGenFramebuffers=shadow_proc<GenFramebuffer>("glGenFramebuffers");
    glDeleteFramebuffers=shadow_proc<DeleteFramebuffer>("glDeleteFramebuffers");
    glBindFramebuffer=shadow_proc<BindFramebuffer>("glBindFramebuffer");
    glFramebufferTexture2D=shadow_proc<AttachFramebuffer>("glFramebufferTexture2D");
    glCheckFramebufferStatus=shadow_proc<CheckFramebuffer>("glCheckFramebufferStatus");
    shadow_gl_context=context;
}
struct ShadowObjects {
    GLuint texture=0, framebuffer=0, depth=0, receiver=0;
    void destroy() {
        if(texture) glDeleteTextures(1,&texture);
        if(framebuffer) glDeleteFramebuffers(1,&framebuffer);
        if(depth) glDeleteProgram(depth);
        if(receiver) glDeleteProgram(receiver);
        *this=ShadowObjects();
    }
};
std::vector<std::pair<HGLRC,ShadowObjects>>& pending_shadows() {
    static std::vector<std::pair<HGLRC,ShadowObjects>> values;return values;
}
void collect_shadow_objects(HGLRC context) {
    auto& pending=pending_shadows();
    for(auto i=pending.begin();i!=pending.end();) {
        if(i->first==context){load_shadow_gl();i->second.destroy();i=pending.erase(i);}else ++i;
    }
}
class ShadowMap;
std::set<ShadowMap*>& live_shadows() {static std::set<ShadowMap*> values;return values;}

struct ShadowState {
    HGLRC context;
    GLint draw_fbo, read_fbo, program, mode, active, array, element;
    ShadowState():context(current_context()) {
        glGetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING,&draw_fbo);
        glGetIntegerv(GL_READ_FRAMEBUFFER_BINDING,&read_fbo);
        glGetIntegerv(GL_CURRENT_PROGRAM,&program);
        glGetIntegerv(GL_MATRIX_MODE,&mode);
        glGetIntegerv(GL_ACTIVE_TEXTURE,&active);
        glGetIntegerv(GL_ARRAY_BUFFER_BINDING,&array);
        glGetIntegerv(GL_ELEMENT_ARRAY_BUFFER_BINDING,&element);
        glPushAttrib(GL_ALL_ATTRIB_BITS);
        glPushClientAttrib(GL_CLIENT_ALL_ATTRIB_BITS);
        glMatrixMode(GL_PROJECTION);glPushMatrix();
        glMatrixMode(GL_MODELVIEW);glPushMatrix();
    }
    ~ShadowState() {
        // Never issue GL calls from arbitrary GC threads or foreign contexts.
        if(wglGetCurrentContext()!=context) return;
        glMatrixMode(GL_MODELVIEW);glPopMatrix();
        glMatrixMode(GL_PROJECTION);glPopMatrix();glMatrixMode(mode);
        glBindFramebuffer(GL_DRAW_FRAMEBUFFER,draw_fbo);
        glBindFramebuffer(GL_READ_FRAMEBUFFER,read_fbo);
        glPopClientAttrib();glPopAttrib();
        glBindBuffer(GL_ARRAY_BUFFER,array);glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,element);
        glUseProgram(program);glActiveTexture(active);
    }
};

class ShadowMap {
    HGLRC owner=nullptr;
    ShadowObjects objects;
    int resolution=0;
    std::unique_ptr<ShadowState> receiving;
    static GLuint shader(GLenum type,const char* text) {
        GLuint id=glCreateShader(type);
        glShaderSource(id,1,&text,nullptr);glCompileShader(id);
        GLint ok=0;glGetShaderiv(id,GL_COMPILE_STATUS,&ok);
        if(!ok) {
            char log[4096]={};glGetShaderInfoLog(id,sizeof(log),nullptr,log);glDeleteShader(id);
            throw std::runtime_error(std::string("Shadow shader: ")+log);
        }
        return id;
    }
    static GLuint program(const char* vertex,const char* fragment) {
        GLuint v=0,f=0,p=0;
        try {
            v=shader(GL_VERTEX_SHADER,vertex);f=shader(GL_FRAGMENT_SHADER,fragment);
            p=glCreateProgram();glAttachShader(p,v);glAttachShader(p,f);glLinkProgram(p);
            GLint ok=0;glGetProgramiv(p,GL_LINK_STATUS,&ok);
            if(!ok) {
                char log[4096]={};glGetProgramInfoLog(p,sizeof(log),nullptr,log);
                throw std::runtime_error(std::string("Shadow program: ")+log);
            }
            glDeleteShader(v);glDeleteShader(f);return p;
        } catch(...) {
            if(v) glDeleteShader(v);if(f) glDeleteShader(f);if(p) glDeleteProgram(p);throw;
        }
    }
    void check() {
        require_context();
        if(owner && owner!=current_context()) throw std::runtime_error("ShadowMap belongs to another GL context");
        load_shadow_gl();
    }
    static void finite(const std::array<float,16>& m) {
        for(float v:m) if(!std::isfinite(v)) throw py::value_error("Invalid shadow matrix");
    }
public:
    size_t updates=0;
    ShadowMap(){live_shadows().insert(this);}
    ~ShadowMap(){
        receiving.reset();
        if(owner) pending_shadows().emplace_back(owner,objects);
        live_shadows().erase(this);
    }
    void close() {
        if(!owner) return;
        check();receiving.reset();objects.destroy();owner=nullptr;resolution=0;
    }
    void close_context(HGLRC context) {if(owner==context) close();}
    void configure(int size) {
        check();
        collect_shadow_objects(current_context());
        if(receiving) throw std::runtime_error("Cannot configure during shadow receiving pass");
        if(size!=512 && size!=1024 && size!=2048 && size!=4096) throw py::value_error("Shadow size must be 512, 1024, 2048 or 4096");
        if(resolution==size) return;
        GLint max_size=0;glGetIntegerv(GL_MAX_TEXTURE_SIZE,&max_size);
        if(size>max_size) throw std::runtime_error("Shadow map exceeds GL texture limit");
        ShadowState state;ShadowObjects next;
        try {
            next.depth=program(
                "#version 120\nvoid main(){gl_Position=gl_ModelViewProjectionMatrix*gl_Vertex;}",
                "#version 120\nvoid main(){gl_FragColor=vec4(1.0);}");
            next.receiver=program(
                "#version 120\nuniform mat4 shadowFromEye;varying vec4 shadowPosition;"
                "void main(){vec4 eye=gl_ModelViewMatrix*gl_Vertex;gl_ClipVertex=eye;"
                "shadowPosition=shadowFromEye*eye;gl_Position=gl_ProjectionMatrix*eye;}",
                "#version 120\nuniform sampler2D shadowDepth;uniform float texel,strength,bias;"
                "varying vec4 shadowPosition;void main(){vec3 p=shadowPosition.xyz/shadowPosition.w;"
                "vec3 dx=dFdx(p),dy=dFdy(p);float det=dx.x*dy.y-dx.y*dy.x;vec2 gradient=vec2(0.0);"
                "if(abs(det)>1e-12)gradient=clamp(vec2(dy.y*dx.z-dx.y*dy.z,dx.x*dy.z-dy.x*dx.z)/det,vec2(-20.0),vec2(20.0));"
                "float safeBias=bias+texel*0.75*(abs(gradient.x)+abs(gradient.y));"
                "float shade=0.0;if(p.x>0.0&&p.x<1.0&&p.y>0.0&&p.y<1.0&&p.z>0.0&&p.z<1.0){"
                "for(int y=-1;y<=1;y++)for(int x=-1;x<=1;x++){"
                "vec2 offset=vec2(float(x),float(y))*texel;float d=texture2D(shadowDepth,p.xy+offset).r;"
                "shade+=(p.z+dot(gradient,offset)-safeBias>d)?1.0:0.0;}}gl_FragColor=vec4(0.0,0.0,0.0,strength*shade/9.0);}");
            glActiveTexture(GL_TEXTURE1);
            glGenTextures(1,&next.texture);glBindTexture(GL_TEXTURE_2D,next.texture);
            glTexImage2D(GL_TEXTURE_2D,0,GL_DEPTH_COMPONENT24,size,size,0,GL_DEPTH_COMPONENT,GL_UNSIGNED_INT,nullptr);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_BORDER);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_BORDER);
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_MODE,GL_NONE);
            GLfloat border[]={1,1,1,1};glTexParameterfv(GL_TEXTURE_2D,GL_TEXTURE_BORDER_COLOR,border);
            glGenFramebuffers(1,&next.framebuffer);glBindFramebuffer(GL_FRAMEBUFFER,next.framebuffer);
            glFramebufferTexture2D(GL_FRAMEBUFFER,GL_DEPTH_ATTACHMENT,GL_TEXTURE_2D,next.texture,0);
            glDrawBuffer(GL_NONE);glReadBuffer(GL_NONE);
            if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)
                throw std::runtime_error("Shadow depth framebuffer is incomplete");
        } catch(...) {next.destroy();throw;}
        objects.destroy();objects=next;owner=current_context();resolution=size;
    }
    void render(DrawList& scene,const std::array<float,16>& light_clip) {
        check();finite(light_clip);
        if(!owner || receiving) throw std::runtime_error("Configure shadow map before rendering");
        ShadowState state;
        glBindFramebuffer(GL_FRAMEBUFFER,objects.framebuffer);
        glViewport(0,0,resolution,resolution);glDrawBuffer(GL_NONE);glReadBuffer(GL_NONE);
        glDisable(GL_SCISSOR_TEST);glDisable(GL_STENCIL_TEST);glDisable(GL_BLEND);
        glDisable(GL_ALPHA_TEST);glDisable(GL_CULL_FACE);glDisable(GL_LIGHTING);
        for(int i=0;i<6;++i) glDisable(GL_CLIP_PLANE0+i);
        glPolygonMode(GL_FRONT_AND_BACK,GL_FILL);
        glColorMask(GL_FALSE,GL_FALSE,GL_FALSE,GL_FALSE);
        glDepthMask(GL_TRUE);glEnable(GL_DEPTH_TEST);glDepthFunc(GL_LESS);
        glClearDepth(1);glClear(GL_DEPTH_BUFFER_BIT);
        glEnable(GL_POLYGON_OFFSET_FILL);glPolygonOffset(2,4);
        glMatrixMode(GL_PROJECTION);glLoadMatrixf(light_clip.data());
        glMatrixMode(GL_MODELVIEW);glLoadIdentity();
        glUseProgram(objects.depth);
        glEnableClientState(GL_VERTEX_ARRAY);glDisableClientState(GL_COLOR_ARRAY);
        glDisableClientState(GL_NORMAL_ARRAY);glDisableClientState(GL_TEXTURE_COORD_ARRAY);
        scene.draw_opaque(false);++updates;
    }
    void begin_receive(const std::array<float,16>& matrix,float strength,float bias) {
        check();finite(matrix);
        if(!std::isfinite(strength)||strength<0||strength>1 || !std::isfinite(bias)||bias<0||bias>.1f)
            throw py::value_error("Invalid shadow strength or bias");
        if(!owner || receiving) throw std::runtime_error("Invalid shadow receive scope");
        receiving=std::make_unique<ShadowState>();
        glUseProgram(objects.receiver);
        glUniformMatrix4fv(glGetUniformLocation(objects.receiver,"shadowFromEye"),1,GL_FALSE,matrix.data());
        glUniform1i(glGetUniformLocation(objects.receiver,"shadowDepth"),1);
        glUniform1f(glGetUniformLocation(objects.receiver,"texel"),1.f/resolution);
        glUniform1f(glGetUniformLocation(objects.receiver,"strength"),strength);
        glUniform1f(glGetUniformLocation(objects.receiver,"bias"),bias);
        glActiveTexture(GL_TEXTURE1);glBindTexture(GL_TEXTURE_2D,objects.texture);
        glActiveTexture(GL_TEXTURE0);
        glEnable(GL_BLEND);glBlendEquation(GL_FUNC_ADD);
        glBlendFuncSeparate(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA,GL_ZERO,GL_ONE);
        glEnable(GL_DEPTH_TEST);glDepthFunc(GL_LEQUAL);glDepthMask(GL_FALSE);
        glDisable(GL_ALPHA_TEST);glDisable(GL_LIGHTING);glDisable(GL_CULL_FACE);
        glEnable(GL_POLYGON_OFFSET_FILL);glPolygonOffset(0,0);
        glEnableClientState(GL_VERTEX_ARRAY);glDisableClientState(GL_COLOR_ARRAY);
        glDisableClientState(GL_NORMAL_ARRAY);glDisableClientState(GL_TEXTURE_COORD_ARRAY);
    }
    void end_receive(){check();receiving.reset();}
};
void release_shadows(HGLRC context) {
    for(auto* shadow:live_shadows()) shadow->close_context(context);
    collect_shadow_objects(context);
    if(shadow_gl_context==context) shadow_gl_context=nullptr;
}
