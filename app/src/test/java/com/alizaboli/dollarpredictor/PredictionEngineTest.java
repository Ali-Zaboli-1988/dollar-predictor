package com.alizaboli.dollarpredictor;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import java.util.ArrayList;
import java.util.Collections;

import org.junit.Test;

public class PredictionEngineTest {
    private final PredictionEngine engine = new PredictionEngine();

    @Test
    public void emptyHistoryProducesNeutralLowInformationResult() {
        PredictionResult result = engine.predict(new ArrayList<>(), Collections.emptyList());

        assertEquals(PredictionResult.Direction.NEUTRAL, result.direction);
        assertEquals(0, result.score);
        assertTrue(result.confidence >= 20 && result.confidence <= 93);
        assertEquals(MarketRegime.Type.CALM, result.regime);
    }

    @Test
    public void strongUpTrendProducesUpSignal() {
        ArrayList<Long> history = new ArrayList<>();
        for (long value = 200; value >= 100; value -= 10) history.add(value);

        PredictionResult result = engine.predict(history, Collections.emptyList());

        assertEquals(PredictionResult.Direction.UP, result.direction);
        assertTrue(result.score >= 8);
        assertTrue(result.trendPct > 0);
        assertTrue(result.backtestSamples >= 5);
    }

    @Test
    public void strongDownTrendProducesDownSignal() {
        ArrayList<Long> history = new ArrayList<>();
        for (long value = 100; value <= 200; value += 10) history.add(value);

        PredictionResult result = engine.predict(history, Collections.emptyList());

        assertEquals(PredictionResult.Direction.DOWN, result.direction);
        assertTrue(result.score <= -8);
        assertTrue(result.trendPct < 0);
        assertTrue(result.backtestSamples >= 5);
    }

    @Test
    public void adverseAndSupportiveNewsChangeDirectionalScore() {
        ArrayList<Long> history = new ArrayList<>();
        for (long value = 140; value >= 100; value -= 4) history.add(value);

        PredictionResult neutralNews = engine.predict(history, Collections.emptyList());
        PredictionResult sanctionsNews = engine.predict(
                history,
                Collections.singletonList("Iran faces new sanctions and financial pressure"));
        PredictionResult diplomacyNews = engine.predict(
                history,
                Collections.singletonList("Iran ceasefire talks and peace agreement continue"));

        assertTrue(sanctionsNews.score > neutralNews.score);
        assertTrue(diplomacyNews.score < neutralNews.score);
        assertTrue(sanctionsNews.factors.size() > 0);
        assertTrue(diplomacyNews.factors.size() > 0);
    }

    @Test
    public void volatilityDoesNotByItselfCreateDirectionalBias() {
        ArrayList<Long> flatHistory = new ArrayList<>();
        for (int i = 0; i < 11; i++) flatHistory.add(100L);

        PredictionResult result = engine.predict(flatHistory, Collections.emptyList());

        assertEquals(0, result.score);
        assertEquals(PredictionResult.Direction.NEUTRAL, result.direction);
        assertEquals(0.0, result.volatilityPct, 0.0001);
    }
}
