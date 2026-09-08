package com.alizaboli.dollarpredictor;

import java.util.Collections;
import java.util.List;

/** Immutable result produced by the prediction engine. */
public final class PredictionResult {
    public enum Direction { UP, DOWN, NEUTRAL }
    public enum RiskLevel { LOW, MEDIUM, HIGH }

    public final Direction direction;
    public final int confidence;
    public final RiskLevel riskLevel;
    public final MarketRegime.Type regime;
    public final int score;
    public final double trendPct;
    public final double volatilityPct;
    public final int backtestSamples;
    public final double backtestAccuracy;
    public final List<String> factors;

    public PredictionResult(
            Direction direction,
            int confidence,
            RiskLevel riskLevel,
            MarketRegime.Type regime,
            int score,
            double trendPct,
            double volatilityPct,
            int backtestSamples,
            double backtestAccuracy,
            List<String> factors) {
        this.direction = direction;
        this.confidence = confidence;
        this.riskLevel = riskLevel;
        this.regime = regime;
        this.score = score;
        this.trendPct = trendPct;
        this.volatilityPct = volatilityPct;
        this.backtestSamples = backtestSamples;
        this.backtestAccuracy = backtestAccuracy;
        this.factors = factors == null
                ? Collections.emptyList()
                : Collections.unmodifiableList(factors);
    }
}
