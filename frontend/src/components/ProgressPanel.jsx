import { Check, LoaderCircle } from "lucide-react";
import { progressStages } from "./progressStages";

export function ProgressPanel({ activeStage }) {
  return (
    <section className="progress-card" aria-live="polite" aria-label="Research progress">
      <div className="progress-heading">
        <LoaderCircle className="spin" size={19} aria-hidden="true" />
        <span>Research in progress</span>
      </div>
      <div className="progress-track" aria-hidden="true">
        <span style={{ width: `${((activeStage + 1) / progressStages.length) * 100}%` }} />
      </div>
      <ol className="progress-steps">
        {progressStages.map((stage, index) => (
          <li key={stage} className={index <= activeStage ? "is-active" : ""}>
            <span className="step-dot">{index < activeStage ? <Check size={12} /> : index + 1}</span>
            {stage}
          </li>
        ))}
      </ol>
    </section>
  );
}
