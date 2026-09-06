package com.alizaboli.dollarpredictor;

import java.util.ArrayList;

/** Detects short-term market regime from the available price history. */
final class MarketRegime {
    enum Type { CALM, TRENDING, VOLATILE, SHOCK }

    final Type type;
    final double volatilityPct;
    final double shortTrendPct;
    final double longTrendPct;
    final int severity;

    private MarketRegime(Type type, double volatilityPct, double shortTrendPct,
                         double longTrendPct, int severity) {
        this.type = type;
        this.volatilityPct = volatilityPct;
        this.shortTrendPct = shortTrendPct;
        this.longTrendPct = longTrendPct;
        this.severity = severity;
    }

    static MarketRegime detect(ArrayList<Long> newestFirst) {
        if (newestFirst == null || newestFirst.size() < 5) {
            return new MarketRegime(Type.CALM, 0.0, 0.0, 0.0, 0);
        }

        int n = newestFirst.size();
        int shortLookback = Math.min(3, n - 1);
        int longLookback = Math.min(10, n - 1);
        double current = newestFirst.get(0);
        double shortOld = newestFirst.get(shortLookback);
        double longOld = newestFirst.get(longLookback);

        double shortTrend = pct(current, shortOld);
        double longTrend = pct(current, longOld);

        double sumSq = 0.0;
        int returns = 0;
        for (int i = 0; i < n - 1; i++) {
            double now = newestFirst.get(i);
            double previous = newestFirst.get(i + 1);
            if (now <= 0 || previous <= 0) continue;
            double move = ((now - previous) / previous) * 100.0;
            sumSq += move * move;
            returns++;
        }
        double volatility = returns == 0 ? 0.0 : Math.sqrt(sumSq / returns);

        int shockCount = 0;
        int severeShockCount = 0;
        for (int i = 0; i < n - 1; i++) {
            double now = newestFirst.get(i);
            double previous = newestFirst.get(i + 1);
            if (now <= 0 || previous <= 0) continue;
            double absMove = Math.abs((now - previous) / previous) * 100.0;
            if (absMove >= 4.0) severeShockCount++;
            if (absMove >= 2.5) shockCount++;
        }

        Type type;
        int severity;
        if (severeShockCount >= 1 || shockCount >= Math.max(2, returns / 5)) {
            type = Type.SHOCK;
            severity = 3;
        } else if (volatility >= 3.0) {
            type = Type.VOLATILE;
            severity = 2;
        } else if (Math.abs(shortTrend) >= 1.5 || Math.abs(longTrend) >= 3.0) {
            type = Type.TRENDING;
            severity = 1;
        } else {
            type = Type.CALM;
            severity = 0;
        }

        return new MarketRegime(type, volatility, shortTrend, longTrend, severity);
    }

    String persianLabel() {
        switch (type) {
            case SHOCK: return "شوک / بحران قیمتی";
            case VOLATILE: return "پرنوسان";
            case TRENDING: return "رونددار";
            default: return "نسبتاً آرام";
        }
    }

    private static double pct(double newer, double older) {
        return older > 0 ? ((newer - older) / older) * 100.0 : 0.0;
    }
}
