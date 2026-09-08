package com.alizaboli.dollarpredictor;

import java.util.ArrayList;
import java.util.List;

/**
 * Reusable, UI-independent prediction logic.
 *
 * Price history must be newest-first, matching MarketRegime.detect().
 * News is optional; recognized terms contribute event pressure only.
 */
public final class PredictionEngine {
    private static final double MIN_CONFIDENCE = 20.0;
    private static final double MAX_CONFIDENCE = 93.0;

    public PredictionResult predict(ArrayList<Long> history, List<String> headlines) {
        ArrayList<Long> safeHistory = history == null ? new ArrayList<>() : history;
        List<String> safeNews = headlines == null ? new ArrayList<>() : headlines;

        HistoryStats stats = historyStats(safeHistory);
        BacktestStats backtest = trendBacktest(safeHistory);
        MarketRegime regime = MarketRegime.detect(safeHistory);
        NewsStats news = newsStats(safeNews);

        int regimeAdjustment = regimeAdjustment(regime, stats.trendPct);
        int score = stats.trendScore
                + stats.volatilityScore
                + backtest.validationScore
                + news.score
                + regimeAdjustment;

        PredictionResult.Direction direction = direction(score);
        int confidence = confidence(score, safeHistory.size(), news.evidenceCount, backtest, regime);
        PredictionResult.RiskLevel risk = riskLevel(regime, stats.volatilityPct, confidence);

        ArrayList<String> factors = new ArrayList<>();
        addFactor(factors, stats.trendScore, "روند تاریخی صعودی", "روند تاریخی نزولی");
        addFactor(factors, stats.volatilityScore, "نوسان بالا", "نوسان پایین");
        addFactor(factors, news.score, "فشار خبری صعودی", "فشار خبری کاهشی");
        addFactor(factors, backtest.validationScore, "اعتبارسنجی روند مناسب", "اعتبارسنجی روند ضعیف");
        switch (regime.type) {
            case SHOCK:
                factors.add("رژیم بازار: شوک / بحران قیمتی");
                break;
            case VOLATILE:
                factors.add("رژیم بازار: پرنوسان");
                break;
            case TRENDING:
                factors.add("رژیم بازار: رونددار");
                break;
            default:
                factors.add("رژیم بازار: نسبتاً آرام");
                break;
        }
        if (news.evidenceCount == 0) {
            factors.add("خبر مرتبط کافی برای امتیازدهی دریافت نشد");
        }

        return new PredictionResult(
                direction,
                confidence,
                risk,
                regime.type,
                score,
                stats.trendPct,
                stats.volatilityPct,
                backtest.samples,
                backtest.accuracy,
                factors);
    }

    private static PredictionResult.Direction direction(int score) {
        if (score >= 8) return PredictionResult.Direction.UP;
        if (score <= -8) return PredictionResult.Direction.DOWN;
        return PredictionResult.Direction.NEUTRAL;
    }

    private static int confidence(int score, int historySize, int evidence, BacktestStats backtest, MarketRegime regime) {
        int confidence = 45 + Math.min(36, Math.abs(score) * 3 + Math.min(14, evidence * 2));
        if (historySize >= 5) confidence += 5;
        if (backtest.samples >= 8) {
            confidence += Math.min(7, backtest.accuracy >= 60.0 ? 7 : backtest.accuracy >= 52.0 ? 4 : 1);
        }
        switch (regime.type) {
            case SHOCK:
                confidence -= 7;
                break;
            case VOLATILE:
                confidence -= 4;
                break;
            case TRENDING:
                confidence += 1;
                break;
            default:
                break;
        }
        if (evidence == 0 && historySize < 5) confidence = 25;
        return clamp(confidence, (int) MIN_CONFIDENCE, (int) MAX_CONFIDENCE);
    }

    private static PredictionResult.RiskLevel riskLevel(MarketRegime regime, double volatilityPct, int confidence) {
        if (regime.type == MarketRegime.Type.SHOCK || volatilityPct >= 3.0 || confidence < 45) {
            return PredictionResult.RiskLevel.HIGH;
        }
        if (regime.type == MarketRegime.Type.VOLATILE || volatilityPct >= 1.5 || confidence < 60) {
            return PredictionResult.RiskLevel.MEDIUM;
        }
        return PredictionResult.RiskLevel.LOW;
    }

    private static int regimeAdjustment(MarketRegime regime, double trendPct) {
        int direction = trendPct > 0.5 ? 1 : trendPct < -0.5 ? -1 : 0;
        switch (regime.type) {
            case SHOCK: return direction * 3;
            case VOLATILE: return direction;
            case TRENDING: return direction * 2;
            default: return 0;
        }
    }

    private static void addFactor(ArrayList<String> factors, int score, String positive, String negative) {
        if (score > 0) factors.add(positive + ": +" + score);
        else if (score < 0) factors.add(negative + ": " + score);
    }

    private static HistoryStats historyStats(ArrayList<Long> history) {
        if (history.size() < 2) return new HistoryStats(0.0, 0.0, 0, 0);
        int lookback = Math.min(10, history.size() - 1);
        double current = history.get(0);
        double old = history.get(lookback);
        double trendPct = old > 0 ? ((current - old) / old) * 100.0 : 0.0;

        int trendScore;
        if (trendPct >= 5.0) trendScore = 4;
        else if (trendPct >= 2.0) trendScore = 2;
        else if (trendPct >= 0.75) trendScore = 1;
        else if (trendPct <= -5.0) trendScore = -4;
        else if (trendPct <= -2.0) trendScore = -2;
        else if (trendPct <= -0.75) trendScore = -1;
        else trendScore = 0;

        double sumSq = 0.0;
        int returns = 0;
        for (int i = 0; i < history.size() - 1; i++) {
            double now = history.get(i);
            double previous = history.get(i + 1);
            if (now <= 0 || previous <= 0) continue;
            double move = ((now - previous) / previous) * 100.0;
            sumSq += move * move;
            returns++;
        }
        double volatility = returns == 0 ? 0.0 : Math.sqrt(sumSq / returns);
        int volatilityScore = volatility >= 3.0 ? 2 : volatility >= 1.5 ? 1 : 0;
        return new HistoryStats(trendPct, volatility, trendScore, volatilityScore);
    }

    private static BacktestStats trendBacktest(ArrayList<Long> history) {
        if (history.size() < 8) return new BacktestStats(0, 0, 0.0, 0);
        int samples = 0;
        int hits = 0;
        int lookback = Math.min(5, history.size() - 2);
        for (int i = history.size() - 2; i >= lookback; i--) {
            long current = history.get(i);
            long oldest = history.get(i + lookback);
            long next = history.get(i - 1);
            if (current <= 0 || oldest <= 0 || next <= 0) continue;
            double trend = ((double) current - oldest) / oldest;
            double actual = ((double) next - current) / current;
            int predicted = trend > 0.003 ? 1 : trend < -0.003 ? -1 : 0;
            int actualDirection = actual > 0 ? 1 : actual < 0 ? -1 : 0;
            if (predicted == 0 || actualDirection == 0) continue;
            samples++;
            if (predicted == actualDirection) hits++;
        }
        double accuracy = samples > 0 ? 100.0 * hits / samples : 0.0;
        int score;
        if (samples < 5) score = 0;
        else if (accuracy >= 65.0) score = 3;
        else if (accuracy >= 58.0) score = 2;
        else if (accuracy >= 52.0) score = 1;
        else if (accuracy <= 35.0) score = -3;
        else if (accuracy <= 42.0) score = -2;
        else if (accuracy <= 48.0) score = -1;
        else score = 0;
        return new BacktestStats(samples, hits, accuracy, score);
    }

    private static NewsStats newsStats(List<String> headlines) {
        int war = 0;
        int sanctions = 0;
        int oil = 0;
        int diplomacy = 0;
        int currency = 0;
        int economy = 0;
        int evidence = 0;

        for (String headline : headlines) {
            if (headline == null) continue;
            String s = headline.toLowerCase(java.util.Locale.ROOT);
            boolean relevant = false;
            if (containsAny(s, "war", "attack", "strike", "missile", "conflict", "escalation", "military", "hormuz", "blockade", "جنگ", "حمله", "موشک", "درگیری")) {
                war += 3; relevant = true;
            }
            if (containsAny(s, "sanction", "sanctions", "secondary sanctions", "treasury", "financial pressure", "تحریم")) {
                sanctions += 3; relevant = true;
            }
            if (containsAny(s, "oil export", "oil exports", "crude", "oil price", "brent", "wti", "tanker", "shipping", "strait of hormuz", "نفت", "صادرات نفت", "هرمز")) {
                oil += 2; relevant = true;
            }
            if (containsAny(s, "ceasefire", "talks", "negotiation", "negotiations", "agreement", "deal", "truce", "de-escalation", "peace", "آتش بس", "مذاکره", "توافق", "صلح")) {
                diplomacy -= 4; relevant = true;
            }
            if (containsAny(s, "central bank", "foreign currency", "fx intervention", "currency intervention", "inject", "reserves", "rial", "dollar", "ارز", "بانک مرکزی", "ریال", "دلار")) {
                relevant = true;
                currency += 1;
                if (containsAny(s, "intervention", "inject", "reserves", "مداخله", "تزریق")) currency -= 3;
            }
            if (containsAny(s, "inflation", "inflationary", "imports", "trade", "economic crisis", "economy", "تورم", "واردات", "بحران اقتصادی")) {
                economy += 2; relevant = true;
            }
            if (relevant) evidence++;
        }

        war = clamp(war, -12, 12);
        sanctions = clamp(sanctions, -12, 12);
        oil = clamp(oil, -10, 10);
        diplomacy = clamp(diplomacy, -12, 12);
        currency = clamp(currency, -8, 8);
        economy = clamp(economy, -10, 10);
        return new NewsStats(war + sanctions + oil + diplomacy + currency + economy, evidence);
    }

    private static boolean containsAny(String text, String... words) {
        for (String word : words) if (text.contains(word)) return true;
        return false;
    }

    private static int clamp(int value, int min, int max) {
        return Math.max(min, Math.min(max, value));
    }

    private static final class HistoryStats {
        final double trendPct;
        final double volatilityPct;
        final int trendScore;
        final int volatilityScore;
        HistoryStats(double trendPct, double volatilityPct, int trendScore, int volatilityScore) {
            this.trendPct = trendPct;
            this.volatilityPct = volatilityPct;
            this.trendScore = trendScore;
            this.volatilityScore = volatilityScore;
        }
    }

    private static final class BacktestStats {
        final int samples;
        final int hits;
        final double accuracy;
        final int validationScore;
        BacktestStats(int samples, int hits, double accuracy, int validationScore) {
            this.samples = samples;
            this.hits = hits;
            this.accuracy = accuracy;
            this.validationScore = validationScore;
        }
    }

    private static final class NewsStats {
        final int score;
        final int evidenceCount;
        NewsStats(int score, int evidenceCount) {
            this.score = score;
            this.evidenceCount = evidenceCount;
        }
    }
}
