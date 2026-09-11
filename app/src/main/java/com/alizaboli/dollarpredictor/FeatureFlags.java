package com.alizaboli.dollarpredictor;

/** Runtime feature switches for experimental predictor components. */
public final class FeatureFlags {
    /** Experimental news scoring is deliberately disabled for production. */
    public static final boolean EXPERIMENTAL_NEWS_ENABLED = false;

    private FeatureFlags() {
    }
}
