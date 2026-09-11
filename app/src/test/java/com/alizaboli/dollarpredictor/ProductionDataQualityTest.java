package com.alizaboli.dollarpredictor;

import org.junit.Test;

import java.util.Arrays;
import java.util.Collections;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public class ProductionDataQualityTest {
    @Test
    public void validPriceAndMoveAreAccepted() {
        assertTrue(ProductionDataQuality.isValidPrice(900_000L));
        assertTrue(ProductionDataQuality.isValidDailyMove(900_000L, 1_000_000L));
    }

    @Test
    public void outOfBoundsAndOversizedMoveAreRejected() {
        assertFalse(ProductionDataQuality.isValidPrice(9_999L));
        assertFalse(ProductionDataQuality.isValidPrice(10_000_001L));
        assertFalse(ProductionDataQuality.isValidDailyMove(900_000L, 1_500_000L));
    }

    @Test
    public void historyRequiresMinimumPointsAndEveryStepValid() {
        assertFalse(ProductionDataQuality.isValidHistory(Collections.nCopies(7, 900_000L)));
        assertTrue(ProductionDataQuality.isValidHistory(Arrays.asList(
                900_000L, 905_000L, 910_000L, 920_000L,
                915_000L, 930_000L, 940_000L, 950_000L)));
        assertFalse(ProductionDataQuality.isValidHistory(Arrays.asList(
                900_000L, 905_000L, 910_000L, 920_000L,
                1_300_000L, 930_000L, 940_000L, 950_000L)));
    }

    @Test
    public void invalidLivePriceFallsBackToValidHistoryPrice() {
        assertEquals(950_000L, ProductionDataQuality.chooseSafePrice(0L,
                Arrays.asList(950_000L, 940_000L)));
        assertEquals(950_000L, ProductionDataQuality.chooseSafePrice(950_000L,
                Arrays.asList(940_000L)));
        assertEquals(0L, ProductionDataQuality.chooseSafePrice(0L, Collections.<Long>emptyList()));
    }
}
