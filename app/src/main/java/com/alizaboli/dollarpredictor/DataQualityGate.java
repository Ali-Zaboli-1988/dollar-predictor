package com.alizaboli.dollarpredictor;

import java.util.ArrayList;
import java.util.List;

/**
 * Runtime input contract for production market data.
 * It is deliberately independent from the prediction weights.
 */
public final class DataQualityGate {
    public static final long MIN_PRICE = 10_000L;
    public static final long MAX_PRICE = 10_000_000L;
    public static final int MIN_HISTORY_POINTS = 8;
    public static final int MAX_HISTORY_POINTS = 365;
    public static final int MAX_HEADLINE_LENGTH = 500;

    private DataQualityGate() {
    }

    public static boolean validCurrentPrice(long price) {
        return price >= MIN_PRICE && price <= MAX_PRICE;
    }

    public static boolean validHistory(List<Long> history) {
        if (history == null || history.size() < MIN_HISTORY_POINTS || history.size() > MAX_HISTORY_POINTS) {
            return false;
        }
        for (Long value : history) {
            if (value == null || !validCurrentPrice(value)) {
                return false;
            }
        }
        return true;
    }

    public static ArrayList<Long> sanitizeHistory(List<Long> history) {
        ArrayList<Long> out = new ArrayList<>();
        if (history == null) return out;
        for (Long value : history) {
            if (value != null && validCurrentPrice(value)) out.add(value);
            if (out.size() == MAX_HISTORY_POINTS) break;
        }
        return out;
    }

    public static boolean validHeadline(String headline) {
        if (headline == null) return false;
        String normalized = headline.trim();
        return !normalized.isEmpty() && normalized.length() <= MAX_HEADLINE_LENGTH;
    }

    public static ArrayList<String> sanitizeHeadlines(List<String> headlines) {
        ArrayList<String> out = new ArrayList<>();
        if (headlines == null) return out;
        for (String headline : headlines) {
            if (validHeadline(headline)) out.add(headline.trim());
            if (out.size() == 12) break;
        }
        return out;
    }
}
