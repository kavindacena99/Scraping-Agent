import { ExternalLink, FileSearch, RotateCcw } from "lucide-react";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";

export function ResearchResult({ result, onReset }) {
  return (
    <section className="result-shell" aria-live="polite">
      <header className="result-header">
        <div>
          <span className="eyebrow">Research complete</span>
          <h2>Research summary</h2>
        </div>
        <button className="secondary-button" type="button" onClick={onReset}>
          <RotateCcw size={16} aria-hidden="true" /> New research
        </button>
      </header>

      <article className="answer-card markdown-body">
        <ReactMarkdown rehypePlugins={[rehypeSanitize]}>{result.answer}</ReactMarkdown>
      </article>

      <div className="result-grid">
        <section className="sources-card">
          <h3>Sources used</h3>
          {result.sources?.length ? (
            <ul className="source-list">
              {result.sources.map((source) => (
                <li key={source.url}>
                  <a href={source.url} target="_blank" rel="noopener noreferrer">
                    <span>{source.title || source.url}</span>
                    <small>{source.url}</small>
                    <ExternalLink size={16} aria-hidden="true" />
                  </a>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">No supporting source pages were available.</p>
          )}
        </section>

        <aside className="metadata-card">
          <FileSearch size={22} aria-hidden="true" />
          <div>
            <strong>{result.pages_scraped}</strong>
            <span>pages analyzed</span>
          </div>
          <div>
            <strong>{result.retrieval_iterations}</strong>
            <span>evidence searches</span>
          </div>
          <div>
            <strong>{result.crawl_iterations}</strong>
            <span>crawl passes</span>
          </div>
        </aside>
      </div>
    </section>
  );
}

