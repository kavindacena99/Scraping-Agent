import { useEffect, useState } from "react";
import { ArrowRight, Globe2, Search, ShieldCheck, Sparkles } from "lucide-react";
import { createResearchJob } from "./api/researchApi";
import { ProgressPanel } from "./components/ProgressPanel";
import { progressStages } from "./components/progressStages";
import { ResearchResult } from "./components/ResearchResult";

const MAX_PROMPT_LENGTH = 4000;

function validateForm(url, prompt) {
  const errors = {};
  if (!url.trim()) errors.url = "Enter the website you want to research.";
  else {
    try {
      const parsed = new URL(url);
      if (!["http:", "https:"].includes(parsed.protocol)) throw new Error();
    } catch {
      errors.url = "Enter a complete HTTP or HTTPS URL.";
    }
  }
  if (!prompt.trim()) errors.prompt = "Describe what you want to find.";
  else if (prompt.length > MAX_PROMPT_LENGTH) errors.prompt = `Keep the prompt under ${MAX_PROMPT_LENGTH} characters.`;
  return errors;
}

export default function App() {
  const [url, setUrl] = useState("");
  const [prompt, setPrompt] = useState("");
  const [errors, setErrors] = useState({});
  const [requestError, setRequestError] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeStage, setActiveStage] = useState(0);
  const [result, setResult] = useState(null);

  useEffect(() => {
    if (!loading) return undefined;
    const timer = window.setInterval(() => {
      setActiveStage((stage) => Math.min(stage + 1, progressStages.length - 1));
    }, 2200);
    return () => window.clearInterval(timer);
  }, [loading]);

  async function handleSubmit(event) {
    event.preventDefault();
    const nextErrors = validateForm(url, prompt);
    setErrors(nextErrors);
    setRequestError("");
    if (Object.keys(nextErrors).length) return;
    setLoading(true);
    setActiveStage(0);
    setResult(null);
    try {
      const data = await createResearchJob({ url: url.trim(), prompt: prompt.trim() });
      setResult(data);
    } catch (error) {
      setRequestError(error.message);
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    setResult(null);
    setRequestError("");
    setActiveStage(0);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="AI Website Research Agent home">
          <span className="brand-mark"><Search size={18} /></span>
          <span>Website Research <b>Agent</b></span>
        </a>
        <span className="trust-note"><ShieldCheck size={15} /> Grounded in website evidence</span>
      </header>

      <div className="ambient ambient-one" aria-hidden="true" />
      <div className="ambient ambient-two" aria-hidden="true" />

      {!result && (
        <section className="research-workspace">
          <div className="intro-block">
            <span className="eyebrow"><Sparkles size={14} /> Agentic website research</span>
            <h1>Ask a website.<br /><span>Get the evidence.</span></h1>
            <p>Point the agent at a public website and describe what matters. It follows relevant pages, evaluates the evidence, and returns a source-linked answer.</p>
          </div>

          <form className="research-form" onSubmit={handleSubmit} noValidate>
            <div className="form-index">01 / Research brief</div>
            <label htmlFor="website-url">Website URL</label>
            <div className={`input-wrap ${errors.url ? "has-error" : ""}`}>
              <Globe2 size={19} aria-hidden="true" />
              <input
                id="website-url"
                type="url"
                value={url}
                onChange={(event) => setUrl(event.target.value)}
                placeholder="https://example.com"
                autoComplete="url"
                disabled={loading}
                aria-describedby={errors.url ? "url-error" : undefined}
              />
            </div>
            {errors.url && <p className="field-error" id="url-error">{errors.url}</p>}

            <div className="label-row">
              <label htmlFor="research-prompt">What would you like to find?</label>
              <span>{prompt.length} / {MAX_PROMPT_LENGTH}</span>
            </div>
            <textarea
              id="research-prompt"
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              placeholder="Find the company's AI products, explain their main features, and identify the industries they serve."
              rows="6"
              disabled={loading}
              aria-describedby={errors.prompt ? "prompt-error" : undefined}
              className={errors.prompt ? "has-error" : ""}
            />
            {errors.prompt && <p className="field-error" id="prompt-error">{errors.prompt}</p>}

            <button className="primary-button" type="submit" disabled={loading}>
              {loading ? "Researching website" : "Research website"}
              {!loading && <ArrowRight size={18} aria-hidden="true" />}
            </button>
            <p className="scope-note">Public HTTP/HTTPS pages only. Private networks and external domains are blocked.</p>
          </form>

          {requestError && <div className="error-banner" role="alert"><strong>Research could not be completed.</strong><span>{requestError}</span></div>}
          {loading && <ProgressPanel activeStage={activeStage} />}
        </section>
      )}

      {result && <ResearchResult result={result} onReset={reset} />}
    </main>
  );
}
