package com.alizaboli.dollarpredictor;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.ArrayList;
import java.util.Arrays;

import org.junit.Test;

public class DataQualityGateTest {
    @Test
    public void acceptsValidCurrentPrice() {
        assertTrue(DataQualityGate.validCurrentPrice(1_500_000L));
        assertFalse(DataQualityGate.validCurrentPrice(9_999L));
        assertFalse(DataQualityGate.validCurrentPrice(10_000_001L));
    }

    @Test
    public void rejectsInvalidHistoryAndSanitizesSafely() {
        ArrayList<Long> valid = new ArrayList<>();
        for (int i = 0; i < 8; i++) valid.add(1_500_000L + i * 1_000L);
        assertTrue(DataQualityGate.validHistory(valid));
        assertFalse(DataQualityGate.validHistory(Arrays.asList(1_500_000L, 1_501_000L)));
        assertFalse(DataQualityGate.validHistory(Arrays.asList(1_500_000L, 0L, 1_501_000L, 1_502_000L,
                1_503_000L, 1_504_000L, 1_505_000L, 1_506_000L)));
        assertTrue(DataQualityGate.sanitizeHistory(Arrays.asList(1_500_000L, 0L, 1_501_000L)).size() == 2);
    }

    @Test
    public void validatesAndBoundsHeadlines() {
        assertTrue(DataQualityGate.validHeadline("Iran currency market update"));
        assertFalse(DataQualityGate.validHeadline("   "));
        assertFalse(DataQualityGate.validHeadline(null));
        StringBuilder longText = new StringBuilder();
        for (int i = 0; i < DataQualityGate.MAX_HEADLINE_LENGTH + 1; i++) longText.append('x');
        assertFalse(DataQualityGate.validHeadline(longText.toString()));
        assertTrue(DataQualityGate.sanitizeHeadlines(Arrays.asList(" A ", null, " ", "B")).size() == 2);
    }
}
