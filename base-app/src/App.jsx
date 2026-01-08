import { Linkedin, Github } from 'lucide-react';
import './App.css';

export default function App() {
  return (
    <div className="min-h-screen w-full bg-white text-black flex flex-col items-center justify-center">
      <h1 className="text-4xl font-bold mb-8">My Portfolio</h1>
      <div className="flex space-x-4">
        <a href="https://linkedin.com/in/your-profile" target="_blank" rel="noopener noreferrer">
          <LinkedIn />
        </a>
        <a href="https://github.com/your-repo" target="_blank" rel="noopener noreferrer">
          <Github />
        </a>
      </div>
      <div className="mt-16">
        <h2 className="text-3xl font-bold mb-4">About Me</h2>
        <p>I am a software developer with experience in building scalable web applications.</p>
      </div>
      <div className="mt-16">
        <h2 className="text-3xl font-bold mb-4">Projects</h2>
        <ul className="list-disc pl-8">
          <li>Project 1: Description of project 1.</li>
          <li>Project 2: Description of project 2.</li>
        </ul>
      </div>
    </div>
  );
}