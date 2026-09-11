package com.alizaboli.dollarpredictor;

import java.util.List;

/**
 * Production-side validation for market data before it reaches the prediction engine.
 * This class is deliberately deterministic and dependency-free so it can be unit tested.
 */
public final class ProductionDataQuality {
    public static final long MIN_PRICE = 10_000L;
    public static final long MAX_PRICE = 10_000_000L;
    public static final double MAX_SINGLE_STEP = 0.25;
    public static final int MIN_HISTORY_POINTS = 8;

    private ProductionDataQuality() {
    }

    public static boolean isValidPrice(long price) {
        return price >= MIN_PRICE && price <= MAX_PRICE;
    }

    public static boolean isValidDailyMove(long previous, long current) {
        if (!isValidPrice(previous) || !isValidPrice(current)) return false;
        return Math.abs((double) current / previous - 1.0) <= MAX_SINGLE_STEP;
    }

    public static boolean isValidHistory(List<Long> closes) {
        if (closes == null || closes.size() < MIN_HISTORY_POINTS) return false;
        for (int i = 0; i < closes.size(); i++) {
            Long value = closes.get(i);
            if (value == null || !isValidPrice(value)) return false;
            if (i > 0 && !isValidDailyMove(closes.get(i - 1), value)) return false;
        }
        return true;
    }

    public static long chooseSafePrice(long livePrice, List<Long> history) {
        if (isValidPrice(livePrice)) return livePrice;
        if (history != null && !history.isEmpty()) {
            Long fallback = history.get(0);
            if (fallback != null && isValidPrice(fallback)) return fallback;
        }
        return 0L;
    }
}
