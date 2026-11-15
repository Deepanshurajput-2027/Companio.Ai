import { useEffect, useRef, useState } from "react";
import { ArrowUp, BriefcaseBusiness, Download, FileText, Github, Globe, Linkedin, Paperclip, Sparkles } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function App() {
  const [profile, setProfile] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [match, setMatch] = useState(null);
  const [busy, setBusy] = useState(false);
  const [matchBusy, setMatchBusy] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef(null);

  useEffect(() => {
    async function fetchProfile() {
      try {
        const response = await fetch(`${API_URL}/api/profile`);
        if (!response.ok) {
          throw new Error("Profile request failed.");
        }
        setProfile(await response.json());
      } catch {
        setError("Could not load the candidate profile.");
      }
    }

    fetchProfile();
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage(event) {
    event?.preventDefault();
    if (!input.trim() || busy) return;
    const question = input.trim();
    const nextMessages = [...messages, { role: "user", content: question }];
    setMessages([...nextMessages, { role: "assistant", content: "" }]);
    setInput(""); setBusy(true); setError("");
    try {
      const response = await fetch(`${API_URL}/api/chat`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: question, history: messages, job_description: jobDescription || null }),
      });
      if (!response.ok) throw new Error((await response.json()).detail || "Chat request failed.");
      if (!response.body) throw new Error("The chat service returned no response body.");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let answer = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        answer += decoder.decode(value, { stream: true });
        setMessages([...nextMessages, { role: "assistant", content: answer }]);
      }
    } catch (requestError) { setError(requestError.message); setMessages(messages); }
    finally { setBusy(false); }
  }

  async function runMatch() {
    if (jobDescription.trim().length < 20 || matchBusy) return;
    setMatchBusy(true); setError("");
    try {
      const response = await fetch(`${API_URL}/api/match`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_description: jobDescription }),
      });
      if (!response.ok) throw new Error((await response.json()).detail || "Match request failed.");
      setMatch(await response.json());
    } catch (requestError) { setError(requestError.message); }
    finally { setMatchBusy(false); }
  }

  async function uploadJob(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    const form = new FormData(); form.append("file", file);
    setMatchBusy(true); setError("");
    try {
      const response = await fetch(`${API_URL}/api/match/upload`, { method: "POST", body: form });
      if (!response.ok) throw new Error((await response.json()).detail || "Upload failed.");
      setMatch(await response.json());
    } catch (requestError) { setError(requestError.message); }
    finally { setMatchBusy(false); }
  }

  async function downloadResume() {
    try {
      const response = await fetch(`${API_URL}/api/resume`);
      if (!response.ok) {
        throw new Error("Resume download is unavailable. Restart the backend service.");
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "Deepanshu_Rajput_Resume.pdf";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  if (!profile) return <main className="loading">Loading Companio<span>.</span></main>;
  return (
    <main className="shell">
      <header className="topbar"><div className="brand"><div className="brand-mark"></div><div><strong>companio<span>.ai</span></strong><small>your candidate, in conversation</small></div></div><div className="status"><i/> Profile active</div></header>
      <section className="hero">
        <p className="eyebrow">AI-powered candidate profile</p>
        <h2>Get to know the candidate before the interview.</h2>
        <p>Chat with my AI representative to explore my experience, projects, and skills. Paste a job description to see how my profile matches the role, including strengths and potential gaps.</p>
      </section>
      <section className="layout">
        <aside className="profile-card">
          
          <h1>{profile.name}</h1><p className="headline">{profile.headline}</p><p className="location">{profile.location}</p>
          <div className="line"/>
          <h3>About this profile</h3><p className="muted">Ask anything about experience, projects, skills, or fit. Answers stay grounded in the facts provided by the candidate.</p>
          <div className="socials">{profile.social_links.github && <a href={profile.social_links.github} target="_blank" rel="noreferrer"><Github size={16}/> GitHub</a>}{profile.social_links.linkedin && <a href={profile.social_links.linkedin} target="_blank" rel="noreferrer"><Linkedin size={16}/> LinkedIn</a>}{profile.social_links.portfolio && <a href={profile.social_links.portfolio} target="_blank" rel="noreferrer"><Globe size={16}/> Portfolio</a>}</div>
          <div className="resume-card"><div className="resume-icon"><FileText size={17}/></div><div className="resume-copy"><strong>Resume</strong><span>PDF · Deepanshu Rajput</span></div><button className="resume-download" onClick={downloadResume} title="Download resume" type="button"><Download size={16}/></button></div>        </aside>
        <section className="chat-card">
          <div className="chat-header"><div><h2>Chat with {profile.name.split(" ")[0]}</h2><p>AI representative · factual and transparent</p></div><div className="online">● online</div></div>
          <div className="messages">
            {messages.length === 0 && <div className="welcome"><div className="welcome-icon"></div><h2>Ask me about the candidate</h2><p>I can walk you through their background, projects, and how they match your role.</p><div className="suggestions">{["Tell me about this candidate.", "What are their strongest projects?", "What skills should I ask about?"].map((item) => <button key={item} onClick={() => setInput(item)}>{item}<ArrowUp size={14}/></button>)}</div></div>}
            {messages.map((message, index) => <div className={`message ${message.role}`} key={`${message.role}-${index}`}><div className="bubble">{message.content ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown> : <span className="typing">Thinking<span>.</span><span>.</span><span>.</span></span>}</div></div>)}
            <div ref={endRef}/>
          </div>
          <form className="composer" onSubmit={sendMessage}><input value={input} onChange={(event) => setInput(event.target.value)} placeholder="Ask a question about the candidate..." disabled={busy}/><button type="submit" disabled={!input.trim() || busy}><ArrowUp size={19}/></button></form>
          <p className="disclaimer">Powered by the candidate profile · No information is invented</p>
        </section>
        <aside className="match-card">
          <div className="match-title"><div className="section-icon"><BriefcaseBusiness size={17}/></div><div><h2>Role match</h2><p>Evaluate against a job description</p></div></div>
          <textarea value={jobDescription} onChange={(event) => setJobDescription(event.target.value)} placeholder="Paste a job description here..."/>
          <div className="match-actions"><label><Paperclip size={15}/> Upload JD<input type="file" accept=".pdf,.docx,.txt" onChange={uploadJob}/></label><button onClick={runMatch} disabled={jobDescription.trim().length < 20 || matchBusy}>{matchBusy ? "Analyzing..." : "Analyze fit"}</button></div>
          {match && <div className="result"><div className="score"><strong>{Math.round(match.score)}%</strong><span>match score</span></div><h3>{match.recommendation}</h3><ResultList title="Strengths" items={match.strengths}/><ResultList title="Missing or unclear" items={match.missing_skills}/></div>}
        </aside>
      </section>
      {error && <div className="error">{error}</div>}
    </main>
  );
}

function ResultList({ title, items }) { return <div className="result-list"><h4>{title}</h4>{items?.length ? <ul>{items.map((item) => <li key={item}>{item}</li>)}</ul> : <p>None identified.</p>}</div>; }

export default App;
