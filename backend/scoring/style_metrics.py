from __future__ import annotations
import logging
from dataclasses import dataclass, fields
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class StyleFingerprint:
    readability: float = 0.0
    avg_sentence_length: float = 0.0
    vocabulary_diversity: float = 0.0
    noun_ratio: float = 0.0
    verb_ratio: float = 0.0
    adjective_ratio: float = 0.0


@dataclass
class ObjectiveReport:
    style_similarity: Optional[float]
    fingerprint: StyleFingerprint
    drift: Optional[float]
    divergence_details: str


class StyleMetrics:
    def __init__(self):
        self._nlp = None

    def _get_nlp(self):
        if self._nlp is None:
            try:
                import spacy

                self._nlp = spacy.load("en_core_web_sm")
                self._nlp.add_pipe("textdescriptives/readability")
                self._nlp.add_pipe("textdescriptives/pos_proportions")
            except Exception as e:
                logger.warning("Failed to load spaCy pipeline: %s", e)
                return None
        return self._nlp

    def compute_fingerprint(self, text: str) -> StyleFingerprint:
        try:
            import textdescriptives as td

            nlp = self._get_nlp()
            if nlp is None:
                return StyleFingerprint()

            doc = nlp(text)
            df = td.extract_df(doc)

            readability = (
                float(df.get("flesch_reading_ease", [0.0])[0])
                if "flesch_reading_ease" in df.columns
                else 0.0
            )

            sents = list(doc.sents)
            avg_sent_len = sum(len(s) for s in sents) / max(len(sents), 1)

            tokens = [t.text.lower() for t in doc if t.is_alpha]
            ttr = len(set(tokens)) / max(len(tokens), 1)

            pos_counts: dict[str, int] = {}
            for token in doc:
                pos_counts[token.pos_] = pos_counts.get(token.pos_, 0) + 1
            total = max(len(doc), 1)

            return StyleFingerprint(
                readability=readability,
                avg_sentence_length=avg_sent_len,
                vocabulary_diversity=ttr,
                noun_ratio=pos_counts.get("NOUN", 0) / total,
                verb_ratio=pos_counts.get("VERB", 0) / total,
                adjective_ratio=pos_counts.get("ADJ", 0) / total,
            )
        except Exception as e:
            logger.warning("StyleMetrics fingerprint failed: %s", e)
            return StyleFingerprint()

    def compute_similarity(
        self, response: str, reference_samples: list[str]
    ) -> Optional[float]:
        if len(reference_samples) < 3:
            return None
        try:
            import math
            from faststylometry import (
                Corpus,
                calculate_burrows_delta,
                tokenise_remove_pronouns_en,
            )

            ref_corpus = Corpus()
            for i, sample in enumerate(reference_samples):
                ref_corpus.add_book(f"author_{i}", f"sample_{i}", sample)

            test_corpus = Corpus()
            test_corpus.add_book("test", "response", response)

            ref_corpus.tokenise(tokenise_remove_pronouns_en)
            test_corpus.tokenise(tokenise_remove_pronouns_en)

            delta_df = calculate_burrows_delta(ref_corpus, test_corpus)
            delta = float(delta_df.values.mean())
            if math.isnan(delta):
                return None
            score = max(0.0, 1.0 - (delta / 3.0))
            return min(score, 1.0)
        except Exception as e:
            logger.warning("StyleMetrics similarity failed: %s", e)
            return None

    def compute_drift(
        self, current: StyleFingerprint, history: list[StyleFingerprint]
    ) -> Optional[float]:
        if not history:
            return None

        n = len(history)
        avg_fields: dict[str, float] = {}
        for f in fields(StyleFingerprint):
            avg_fields[f.name] = sum(getattr(h, f.name) for h in history) / n

        squared_diffs: list[float] = []
        for f in fields(StyleFingerprint):
            diff = getattr(current, f.name) - avg_fields[f.name]
            squared_diffs.append(diff**2)

        return (sum(squared_diffs) / len(squared_diffs)) ** 0.5

    def analyze(
        self,
        response: str,
        reference_samples: list[str],
        fingerprint_history: list[StyleFingerprint],
    ) -> ObjectiveReport:
        fingerprint = self.compute_fingerprint(response)
        similarity = self.compute_similarity(response, reference_samples)
        drift = self.compute_drift(fingerprint, fingerprint_history)

        details_parts: list[str] = []
        if similarity is not None:
            details_parts.append(f"style_similarity={similarity:.2f}")
        if drift is not None:
            details_parts.append(f"drift={drift:.3f}")
            if drift > 0.3 and fingerprint_history:
                n = len(fingerprint_history)
                for f in fields(StyleFingerprint):
                    avg = sum(getattr(h, f.name) for h in fingerprint_history) / n
                    curr = getattr(fingerprint, f.name)
                    if abs(curr - avg) > 0.2 * max(abs(avg), 1.0):
                        details_parts.append(f"{f.name}: {avg:.1f} → {curr:.1f}")

        return ObjectiveReport(
            style_similarity=similarity,
            fingerprint=fingerprint,
            drift=drift,
            divergence_details=", ".join(details_parts) if details_parts else "",
        )
