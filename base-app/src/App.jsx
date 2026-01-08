import React, { useState, useEffect } from 'react';
import { createClient } from '@supabase/supabase-js';
import { 
  Github, 
  Linkedin, 
  Mail, 
  ExternalLink, 
  Plus, 
  Trash2, 
  User, 
  LogOut, 
  Briefcase, 
  Code, 
  Send
} from 'lucide-react';

const supabase = createClient('', '');

const App = () => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [authMode, setAuthMode] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [projects, setProjects] = useState([]);
  const [formData, setFormData] = useState({ title: '', description: '', link: '', tech: '' });

  useEffect(() => {
    const session = supabase.auth.getSession();
    setUser(session?.user ?? null);
    
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });

    fetchProjects();

    return () => subscription.unsubscribe();
  }, []);

  const fetchProjects = async () => {
    const { data, error } = await supabase
      .from('app_universal')
      .select('*')
      .eq('collection', 'fa_a_um_template_de_');
    if (!error && data) setProjects(data);
    setLoading(false);
  };

  const handleAuth = async (e) => {
    e.preventDefault();
    if (authMode === 'login') {
      await supabase.auth.signInWithPassword({ email, password });
    } else {
      await supabase.auth.signUp({ email, password });
    }
  };

  const handleSignOut = async () => {
    await supabase.auth.signOut();
  };

  const addProject = async (e) => {
    e.preventDefault();
    const newProject = {
      ...formData,
      email: user.email,
      imageId: Math.floor(Math.random() * 1000)
    };
    const { error } = await supabase
      .from('app_universal')
      .insert([{ collection: 'fa_a_um_template_de_', data: newProject }]);
    
    if (!error) {
      setFormData({ title: '', description: '', link: '', tech: '' });
      fetchProjects();
    }
  };

  const deleteProject = async (id) => {
    await supabase.from('app_universal').delete().eq('id', id);
    fetchProjects();
  };

  if (!user) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
        <div className="bg-slate-800 p-8 rounded-2xl w-full max-w-md border border-slate-700 shadow-xl">
          <h2 className="text-3xl font-bold text-white mb-6 text-center">Portfolio CMS</h2>
          <form onSubmit={handleAuth} className="space-y-4">
            <input
              type="email"
              placeholder="Email"
              className="w-full bg-slate-900 border border-slate-700 p-3 rounded-lg text-white outline-none focus:border-blue-500"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <input
              type="password"
              placeholder="Senha"
              className="w-full bg-slate-900 border border-slate-700 p-3 rounded-lg text-white outline-none focus:border-blue-500"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <button className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-lg transition-colors">
              {authMode === 'login' ? 'Entrar' : 'Cadastrar'}
            </button>
          </form>
          <button 
            onClick={() => setAuthMode(authMode === 'login' ? 'register' : 'login')}
            className="w-full text-slate-400 mt-4 text-sm hover:text-white"
          >
            {authMode === 'login' ? 'Não tem conta? Crie uma' : 'Já tem conta? Faça login'}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-sans">
      <nav className="border-b border-slate-800 bg-slate-950/50 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Code className="text-blue-500" />
            <span className="font-bold text-xl tracking-tight text-white">DEV.PORTFOLIO</span>
          </div>
          <div className="flex items-center gap-6">
            <div className="hidden md:flex gap-6 text-sm font-medium">
              <a href="#projects" className="hover:text-blue-500 transition-colors">Projetos</a>
              <a href="#manage" className="hover:text-blue-500 transition-colors">Gerenciar</a>
            </div>
            <button onClick={handleSignOut} className="flex items-center gap-2 text-red-400 hover:text-red-300 text-sm">
              <LogOut size={18} />
              Sair
            </button>
          </div>
        </div>
      </nav>

      <header className="py-24 px-6 relative overflow-hidden">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full bg-blue-600/10 blur-[120px] rounded-full -z-10" />
        <div className="max-w-4xl mx-auto text-center">
          <img src={`https://i.pravatar.cc/150?u=${user.id}`} alt="Avatar" className="w-32 h-32 rounded-full mx-auto mb-8 border-4 border-blue-600 p-1" />
          <h1 className="text-5xl md:text-7xl font-black text-white mb-6">
            Olá, eu sou <span className="text-blue-500">Desenvolvedor</span>
          </h1>
          <p className="text-xl text-slate-400 mb-10 max-w-2xl mx-auto">
            Transformando ideias complexas em experiências digitais elegantes e escaláveis. Especialista em React e ecossistemas modernos.
          </p>
          <div className="flex justify-center gap-4">
            <button className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-full font-bold flex items-center gap-2 transition-all transform hover:scale-105">
              <Mail size={20} /> Contato
            </button>
            <div className="flex gap-2">
              <a href="#" className="p-3 bg-slate-800 rounded-full hover:bg-slate-700 transition-colors"><Github /></a>
              <a href="#" className="p-3 bg-slate-800 rounded-full hover:bg-slate-700 transition-colors"><Linkedin /></a>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-20 space-y-32">
        <section id="projects">
          <div className="flex items-center gap-4 mb-12">
            <Briefcase className="text-blue-500" size={32} />
            <h2 className="text-4xl font-bold text-white">Meus Projetos</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {projects.map((project) => (
              <div key={project.id} className="group bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden hover:border-blue-500/50 transition-all shadow-lg">
                <div className="relative h-48 overflow-hidden">
                  <img 
                    src={`https://picsum.photos/id/${project.data.imageId}/800/600`} 
                    alt={project.data.title}
                    className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-slate-900 to-transparent opacity-60" />
                </div>
                <div className="p-6">
                  <span className="text-xs font-bold text-blue-500 uppercase tracking-widest">{project.data.tech}</span>
                  <h3 className="text-xl font-bold text-white mt-2 mb-3">{project.data.title}</h3>
                  <p className="text-slate-400 text-sm mb-6 line-clamp-2">{project.data.description}</p>
                  <div className="flex justify-between items-center">
                    <a href={project.data.link} className="flex items-center gap-2 text-white hover:text-blue-400 transition-colors font-medium">
                      Ver Projeto <ExternalLink size={16} />
                    </a>
                    {user.email === project.data.email && (
                      <button onClick={() => deleteProject(project.id)} className="text-slate-600 hover:text-red-500 transition-colors">
                        <Trash2 size={18} />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section id="manage" className="bg-slate-900 p-8 md:p-12 rounded-3xl border border-slate-800">
          <div className="max-w-2xl mx-auto">
            <div className="text-center mb-10">
              <h2 className="text-3xl font-bold text-white mb-2">Novo Projeto</h2>
              <p className="text-slate-400">Adicione um novo item ao seu portfólio público</p>
            </div>
            <form onSubmit={addProject} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <label className="text-sm font-semibold text-slate-400">Título</label>
                  <input
                    required
                    className="w-full bg-slate-950 border border-slate-800 p-4 rounded-xl text-white outline-none focus:border-blue-500 transition-all"
                    value={formData.title}
                    onChange={e => setFormData({...formData, title: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-semibold text-slate-400">Tecnologias</label>
                  <input
                    required
                    placeholder="React, Tailwind, Node..."
                    className="w-full bg-slate-950 border border-slate-800 p-4 rounded-xl text-white outline-none focus:border-blue-500 transition-all"
                    value={formData.tech}
                    onChange={e => setFormData({...formData, tech: e.target.value})}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-semibold text-slate-400">URL do Projeto</label>
                <input
                  required
                  type="url"
                  className="w-full bg-slate-950 border border-slate-800 p-4 rounded-xl text-white outline-none focus:border-blue-500 transition-all"
                  value={formData.link}
                  onChange={e => setFormData({...formData, link: e.target.value})}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-semibold text-slate-400">Descrição</label>
                <textarea
                  required
                  rows="4"
                  className="w-full bg-slate-950 border border-slate-800 p-4 rounded-xl text-white outline-none focus:border-blue-500 transition-all"
                  value={formData.description}
                  onChange={e => setFormData({...formData, description: e.target.value})}
                />
              </div>
              <button className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-4 rounded-xl flex items-center justify-center gap-2 transition-transform active:scale-95 shadow-lg shadow-blue-500/20">
                <Plus size={20} /> Salvar Projeto
              </button>
            </form>
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-900 py-12 mt-20">
        <div className="max-w-6xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-8">
          <div className="text-slate-500 text-sm">
            © {new Date().getFullYear()} - {user.email}
          </div>
          <div className="flex gap-8 text-slate-400">
            <a href="#" className="hover:text-blue-500 transition-colors">Stack Overflow</a>
            <a href="#" className="hover:text-blue-500 transition-colors">Dribbble</a>
            <a href="#" className="hover:text-blue-500 transition-colors">Behance</a>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;