package com.alizaboli.dollarpredictor;

import android.app.Activity;
import android.os.Bundle;
import android.graphics.Color;
import android.graphics.Typeface;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import org.xmlpull.v1.XmlPullParser;
import org.xmlpull.v1.XmlPullParserFactory;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.text.NumberFormat;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private LinearLayout root;
    private TextView priceView, signalView, rangeView, factorsView, historyView, scenariosView, explanationView, newsView, updatedView;
    private final ExecutorService executor = Executors.newSingleThreadExecutor();

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        buildUi();
        refresh();
    }

    private TextView text(String value, float size, boolean bold) {
        TextView t = new TextView(this);
        t.setText(value);
        t.setTextSize(size);
        t.setTextColor(Color.rgb(30, 30, 35));
        t.setGravity(Gravity.RIGHT);
        t.setPadding(24, 16, 24, 16);
        if (bold) t.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        return t;
    }

    private void buildUi() {
        ScrollView scroll = new ScrollView(this);
        root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(18, 18, 18, 24);
        root.setLayoutDirection(View.LAYOUT_DIRECTION_RTL);
        scroll.addView(root);
        setContentView(scroll);

        TextView title = text("پیش‌بینی هوشمند دلار", 27, true);
        title.setGravity(Gravity.CENTER);
        root.addView(title);
        TextView sub = text("تحلیل بازار آزاد + روند تاریخی + جنگ + تحریم + نفت + سیاست + اخبار", 15, false);
        sub.setGravity(Gravity.CENTER);
        root.addView(sub);

        priceView = text("قیمت دلار\nدر حال دریافت...", 25, true);
        priceView.setGravity(Gravity.CENTER);
        root.addView(card(priceView));

        signalView = text("سیگنال: در حال تحلیل...", 20, true);
        root.addView(card(signalView));

        rangeView = text("بازه احتمالی ۲۴ ساعت آینده: —", 17, false);
        root.addView(card(rangeView));

        factorsView = text("عوامل مؤثر\n—", 16, false);
        root.addView(card(factorsView));

        historyView = text("روند تاریخی\nدر حال دریافت داده...", 16, false);
        root.addView(card(historyView));

        scenariosView = text("سناریوها\n—", 16, false);
        root.addView(card(scenariosView));

        explanationView = text("تحلیل: —", 16, false);
        root.addView(card(explanationView));

        Button refresh = new Button(this);
        refresh.setText("به‌روزرسانی و تحلیل مجدد");
        refresh.setOnClickListener(v -> refresh());
        root.addView(refresh);

        updatedView = text("آخرین بروزرسانی: —", 13, false);
        root.addView(updatedView);

        root.addView(text("اخبار مؤثر بر بازار", 20, true));
        newsView = text("در حال دریافت اخبار...", 15, false);
        root.addView(card(newsView));

        TextView disclaimer = text("توجه: این برنامه مدل احتمالی است و توصیه خرید یا فروش ارز نیست. درصد اطمینان، اطمینان مدل به جهت حرکت است و احتمال قطعی وقوع را تضمین نمی‌کند.", 13, false);
        disclaimer.setTextColor(Color.DKGRAY);
        root.addView(disclaimer);
    }

    private View card(View v) {
        v.setBackgroundColor(Color.rgb(245, 245, 247));
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(-1, -2);
        p.setMargins(0, 8, 0, 8);
        v.setLayoutParams(p);
        return v;
    }

    private void refresh() {
        priceView.setText("قیمت دلار\nدر حال دریافت...");
        signalView.setText("سیگنال: در حال تحلیل...");
        factorsView.setText("عوامل مؤثر\nدر حال محاسبه...");
        historyView.setText("روند تاریخی\nدر حال دریافت داده...");
        scenariosView.setText("سناریوها\nدر حال محاسبه...");

        executor.execute(() -> {
            long price = fetchDollarPrice();
            ArrayList<String> headlines = fetchNews();
            ArrayList<Long> history = fetchHistoricalCloses();
            Prediction prediction = analyze(price, history, headlines);
            runOnUiThread(() -> showResult(price, history, headlines, prediction));
        });
    }

    private long fetchDollarPrice() {
        String[] urls = {
                "https://www.tgju.org/profile/price_dollar_rl",
                "https://bonbast.com/"
        };
        for (String u : urls) {
            try {
                String html = get(u);
                long raw = extractPrice(html);
                if (raw <= 0) continue;
                if (raw >= 500000) return raw / 10;
                if (raw >= 10000) return raw;
            } catch (Exception ignored) {}
        }
        return 0;
    }

    private long extractPrice(String html) {
        String normalized = normalizeDigits(html);
        String[] patterns = {
                "(?i)دلار.{0,250}?([0-9]{1,3}(?:[,،][0-9]{3}){1,2})",
                "(?i)(?:sell|selling|price).{0,100}?([0-9]{1,3}(?:[,][0-9]{3}){1,2})",
                "(?:قیمت|فروش).{0,100}?([0-9]{5,7})"
        };
        for (String s : patterns) {
            Matcher m = Pattern.compile(s, Pattern.DOTALL).matcher(normalized);
            if (m.find()) {
                String n = m.group(1).replace(",", "").replace("،", "");
                try { return Long.parseLong(n); } catch (Exception ignored) {}
            }
        }
        return 0;
    }

    private ArrayList<Long> fetchHistoricalCloses() {
        ArrayList<Long> closes = new ArrayList<>();
        String[] urls = {
                "https://english.tgju.org/profile/price_dollar_rl/history",
                "https://www.tgju.org/profile/price_dollar_rl/charts-data/history"
        };

        for (String url : urls) {
            try {
                String raw = get(url);
                String normalized = normalizeDigits(raw);
                normalized = normalized.replaceAll("<[^>]+>", " ").replaceAll("&nbsp;", " ").replaceAll("\\s+", " ");
                Pattern row = Pattern.compile(
                        "([0-9]{1,3}(?:,[0-9]{3}){1,2})\\s+" +
                        "([0-9]{1,3}(?:,[0-9]{3}){1,2})\\s+" +
                        "([0-9]{1,3}(?:,[0-9]{3}){1,2})\\s+" +
                        "([0-9]{1,3}(?:,[0-9]{3}){1,2})\\s+" +
                        "(?:[-0-9.,%]+)\\s+" +
                        "(?:[0-9./-]+)");
                Matcher m = row.matcher(normalized);
                while (m.find() && closes.size() < 30) {
                    String close = m.group(4).replace(",", "");
                    try {
                        long value = Long.parseLong(close);
                        if (value > 100000) value /= 10;
                        if (value >= 10000 && value <= 1000000) closes.add(value);
                    } catch (Exception ignored) {}
                }
                if (closes.size() >= 5) return closes;
                closes.clear();
            } catch (Exception ignored) {}
        }
        return closes;
    }

    private String normalizeDigits(String value) {
        if (value == null) return "";
        return value
                .replace('۰','0').replace('۱','1').replace('۲','2').replace('۳','3').replace('۴','4')
                .replace('۵','5').replace('۶','6').replace('۷','7').replace('۸','8').replace('۹','9');
    }

    private ArrayList<String> fetchNews() {
        ArrayList<String> out = new ArrayList<>();
        Set<String> seen = new HashSet<>();
        String[] feeds = {
                "https://news.google.com/rss/search?q=Iran+dollar+OR+Iran+economy+OR+Iran+sanctions+OR+Iran+oil+OR+Iran+war+OR+Iran+ceasefire&hl=en-US&gl=US&ceid=US:en",
                "https://news.google.com/rss/search?q=Iran+currency+OR+Iran+negotiations+OR+Strait+of+Hormuz&hl=en-US&gl=US&ceid=US:en"
        };
        for (String feed : feeds) {
            try {
                String xml = get(feed);
                XmlPullParserFactory f = XmlPullParserFactory.newInstance();
                XmlPullParser x = f.newPullParser();
                x.setInput(new java.io.StringReader(xml));
                int event;
                boolean item = false;
                while ((event = x.next()) != XmlPullParser.END_DOCUMENT && out.size() < 12) {
                    if (event == XmlPullParser.START_TAG && "item".equals(x.getName())) item = true;
                    else if (event == XmlPullParser.END_TAG && "item".equals(x.getName())) item = false;
                    else if (item && event == XmlPullParser.START_TAG && "title".equals(x.getName())) {
                        String title = x.nextText();
                        if (title != null) {
                            title = title.trim();
                            String key = title.toLowerCase(Locale.ROOT).replaceAll("\\s+", " ");
                            if (!key.isEmpty() && seen.add(key)) out.add(title);
                        }
                    }
                }
            } catch (Exception ignored) {}
        }
        return out;
    }

    private Prediction analyze(long price, ArrayList<Long> history, ArrayList<String> news) {
        int war = 0, sanctions = 0, oil = 0, diplomacy = 0, currency = 0, economy = 0;
        int totalEvidence = 0;
        StringBuilder evidence = new StringBuilder();
        Set<String> evidenceSeen = new HashSet<>();

        for (String headline : news) {
            String s = headline.toLowerCase(Locale.ROOT);
            boolean relevant = false;

            if (containsAny(s, "war", "attack", "strike", "missile", "conflict", "escalation", "military", "hormuz", "blockade", "جنگ", "حمله", "موشک", "درگیری")) {
                war += 3; relevant = true;
            }
            if (containsAny(s, "sanction", "sanctions", "secondary sanctions", "treasury", "financial pressure", "تحریم", "خزانه داری")) {
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
                if (containsAny(s, "intervention", "inject", "reserves", "enough foreign currency", "مداخله", "تزریق")) currency -= 3;
            }
            if (containsAny(s, "inflation", "inflationary", "imports", "trade", "economic crisis", "economy", "تورم", "واردات", "بحران اقتصادی")) {
                economy += 2; relevant = true;
            }

            if (relevant) {
                totalEvidence++;
                String key = headline.toLowerCase(Locale.ROOT).replaceAll("\\s+", " ");
                if (evidenceSeen.add(key)) evidence.append("• ").append(headline).append("\n");
            }
        }

        war = cap(war, -12, 12);
        sanctions = cap(sanctions, -12, 12);
        oil = cap(oil, -10, 10);
        diplomacy = cap(diplomacy, -12, 12);
        currency = cap(currency, -8, 8);
        economy = cap(economy, -10, 10);

        HistoryStats hs = calculateHistory(history);
        int trendScore = hs.trendScore;
        int volatilityScore = hs.volatilityScore;
        int weighted = war + sanctions + oil + diplomacy + currency + economy + trendScore + volatilityScore;

        int confidence = 45 + Math.min(38, Math.abs(weighted) * 3 + Math.min(14, totalEvidence * 2));
        if (history.size() >= 5) confidence += 5;
        if (totalEvidence == 0 && history.size() < 5) confidence = 25;
        confidence = cap(confidence, 20, 93);

        String signal;
        if (weighted >= 8) signal = "احتمال افزایش 🔴";
        else if (weighted <= -8) signal = "احتمال کاهش 🟢";
        else signal = "نوسانی / نامشخص 🟡";

        long base = price > 0 ? price : (history.isEmpty() ? 220000 : history.get(0));
        double historyMove = hs.volatilityPct > 0 ? Math.min(0.055, Math.max(0.012, hs.volatilityPct * 1.15 / 100.0)) : 0.018;
        double move24 = weighted >= 8 ? Math.max(0.032, historyMove) : weighted <= -8 ? Math.max(0.024, historyMove * 0.9) : Math.max(0.016, historyMove * 0.75);
        if (weighted >= 14) move24 = Math.max(move24, 0.050);
        if (weighted <= -14) move24 = Math.max(move24, 0.040);

        long low24 = Math.round(base * (weighted >= 0 ? 1.0 - move24 * 0.55 : 1.0 - move24));
        long high24 = Math.round(base * (weighted >= 0 ? 1.0 + move24 : 1.0 + move24 * 0.55));

        double threeDayMove = Math.min(0.11, move24 * 1.75);
        double sevenDayMove = Math.min(0.20, move24 * 2.7);
        long threeLow = Math.round(base * (weighted >= 0 ? 1.0 - threeDayMove * 0.45 : 1.0 - threeDayMove));
        long threeHigh = Math.round(base * (weighted >= 0 ? 1.0 + threeDayMove : 1.0 + threeDayMove * 0.45));
        long sevenLow = Math.round(base * (weighted >= 0 ? 1.0 - sevenDayMove * 0.40 : 1.0 - sevenDayMove));
        long sevenHigh = Math.round(base * (weighted >= 0 ? 1.0 + sevenDayMove : 1.0 + sevenDayMove * 0.40));

        String explanation;
        if (weighted >= 8) explanation = "هم خبرهای پرریسک و هم روند تاریخی، متمایل به افزایش‌اند؛ مدل احتمال تداوم فشار صعودی و نوسان بالا را بیشتر می‌داند.";
        else if (weighted <= -8) explanation = "وزن عوامل کاهنده بیشتر است و روند تاریخی نیز از سناریوی اصلاحی حمایت می‌کند؛ با این حال خبرهای سیاسی می‌توانند مسیر را سریع عوض کنند.";
        else explanation = "سیگنال‌های خبری و روند تاریخی کاملاً هم‌جهت نیستند؛ بنابراین مدل نوسان و واکنش شدید به خبر جدید را محتمل‌تر می‌داند.";

        if (evidence.length() == 0) evidence.append("• خبر مرتبط کافی برای تحلیل وزن‌دار دریافت نشد.\n");

        return new Prediction(signal, confidence, low24, high24, threeLow, threeHigh, sevenLow, sevenHigh,
                war, sanctions, oil, diplomacy, currency, economy, trendScore, volatilityScore, weighted,
                hs.trendPct, hs.volatilityPct, explanation, evidence.toString(), history.size());
    }

    private HistoryStats calculateHistory(ArrayList<Long> history) {
        if (history == null || history.size() < 2) return new HistoryStats(0, 0, 0, 0);
        int n = history.size();
        int lookback = Math.min(10, n - 1);
        double recent = history.get(0);
        double old = history.get(lookback);
        double trendPct = old > 0 ? ((recent - old) / old) * 100.0 : 0;

        int trendScore = 0;
        if (trendPct >= 5.0) trendScore = 4;
        else if (trendPct >= 2.0) trendScore = 2;
        else if (trendPct >= 0.75) trendScore = 1;
        else if (trendPct <= -5.0) trendScore = -4;
        else if (trendPct <= -2.0) trendScore = -2;
        else if (trendPct <= -0.75) trendScore = -1;

        double sumAbs = 0;
        double sumSq = 0;
        int returns = 0;
        for (int i = 0; i < n - 1; i++) {
            double a = history.get(i);
            double b = history.get(i + 1);
            if (b <= 0) continue;
            double r = ((a - b) / b) * 100.0;
            sumAbs += Math.abs(r);
            sumSq += r * r;
            returns++;
        }
        double volatilityPct = returns > 0 ? Math.sqrt(sumSq / returns) : 0;
        int volatilityScore = volatilityPct >= 3.0 ? 2 : volatilityPct >= 1.5 ? 1 : 0;
        return new HistoryStats(trendPct, volatilityPct, trendScore, volatilityScore);
    }

    private boolean containsAny(String text, String... words) {
        for (String word : words) if (text.contains(word)) return true;
        return false;
    }

    private int cap(int value, int min, int max) {
        return Math.max(min, Math.min(max, value));
    }

    private void showResult(long price, ArrayList<Long> history, ArrayList<String> news, Prediction p) {
        long base = price > 0 ? price : (history.isEmpty() ? 220000 : history.get(0));
        priceView.setText(price > 0 ? "قیمت تقریبی دلار\n" + format(price) + " تومان" : "قیمت دلار\nدریافت نشد");
        signalView.setText("سیگنال ۲۴ ساعته: " + p.signal + "\nدرصد اطمینان مدل: " + p.confidence + "%");
        rangeView.setText("بازه احتمالی ۲۴ ساعت آینده\n" + format(p.low24) + " تا " + format(p.high24) + " تومان");

        factorsView.setText(
                "عوامل مؤثر در مدل\n" +
                "جنگ و تنش: " + signed(p.war) + "\n" +
                "تحریم و فشار مالی: " + signed(p.sanctions) + "\n" +
                "نفت و صادرات/حمل‌ونقل: " + signed(p.oil) + "\n" +
                "مذاکره و کاهش تنش: " + signed(p.diplomacy) + "\n" +
                "ارز و مداخله بانک مرکزی: " + signed(p.currency) + "\n" +
                "اقتصاد و تورم: " + signed(p.economy) + "\n" +
                "روند تاریخی: " + signed(p.trendScore) + "\n" +
                "نوسان تاریخی: " + signed(p.volatilityScore) + "\n" +
                "امتیاز نهایی: " + signed(p.weighted));

        historyView.setText(
                "روند تاریخی دلار\n" +
                "تعداد داده‌های روزانه دریافت‌شده: " + p.historyCount + "\n" +
                "روند " + Math.min(10, Math.max(1, p.historyCount - 1)) + " روز اخیر: " + signedPercent(p.trendPct) + "\n" +
                "نوسان روزانه محاسبه‌شده: " + formatPercent(p.volatilityPct) + "\n" +
                "اثر روند بر مدل: " + signed(p.trendScore));

        scenariosView.setText(
                "سناریوهای قیمتی بر اساس قیمت فعلی " + format(base) + " تومان\n\n" +
                "۲۴ ساعت: " + format(p.low24) + " تا " + format(p.high24) + "\n" +
                "۳ روز: " + format(p.threeLow) + " تا " + format(p.threeHigh) + "\n" +
                "۷ روز: " + format(p.sevenLow) + " تا " + format(p.sevenHigh) + "\n\n" +
                "سناریوی پایه: ادامه وضعیت فعلی با نوسان\n" +
                "سناریوی مثبت: کاهش تنش/مذاکره یا افزایش عرضه ارز\n" +
                "سناریوی بحرانی: تشدید جنگ/تحریم/اختلال صادرات نفت");

        explanationView.setText("تحلیل مدل\n" + p.explanation + "\n\nاخبار واردشده به مدل:\n" + p.evidence);

        StringBuilder n = new StringBuilder();
        if (news.isEmpty()) n.append("خبر جدیدی دریافت نشد.");
        else for (int i = 0; i < news.size(); i++) n.append(i + 1).append(". ").append(news.get(i)).append("\n\n");
        newsView.setText(n.toString());
        updatedView.setText("آخرین بروزرسانی: همین الان | " + news.size() + " خبر | " + p.historyCount + " رکورد تاریخی");
    }

    private String signed(int n) { return n > 0 ? "+" + n : String.valueOf(n); }
    private String signedPercent(double n) { return (n > 0 ? "+" : "") + String.format(Locale.US, "%.2f%%", n); }
    private String formatPercent(double n) { return String.format(Locale.US, "%.2f%%", n); }

    private String format(long n) {
        return NumberFormat.getNumberInstance(Locale.US).format(n);
    }

    private String get(String url) throws Exception {
        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
        c.setConnectTimeout(12000);
        c.setReadTimeout(15000);
        c.setRequestProperty("User-Agent", "Mozilla/5.0 (Android; DollarPredictor)");
        c.setRequestMethod("GET");
        InputStream in = c.getResponseCode() < 400 ? c.getInputStream() : c.getErrorStream();
        if (in == null) throw new IllegalStateException("Empty HTTP response");
        BufferedReader r = new BufferedReader(new InputStreamReader(in));
        StringBuilder b = new StringBuilder();
        String line;
        while ((line = r.readLine()) != null) b.append(line).append('\n');
        r.close();
        c.disconnect();
        return b.toString();
    }

    @Override protected void onDestroy() {
        super.onDestroy();
        executor.shutdownNow();
    }

    private static class HistoryStats {
        final double trendPct, volatilityPct;
        final int trendScore, volatilityScore;
        HistoryStats(double trendPct, double volatilityPct, int trendScore, int volatilityScore) {
            this.trendPct = trendPct;
            this.volatilityPct = volatilityPct;
            this.trendScore = trendScore;
            this.volatilityScore = volatilityScore;
        }
    }

    private static class Prediction {
        final String signal, explanation, evidence;
        final int confidence, war, sanctions, oil, diplomacy, currency, economy, trendScore, volatilityScore, weighted, historyCount;
        final long low24, high24, threeLow, threeHigh, sevenLow, sevenHigh;
        final double trendPct, volatilityPct;

        Prediction(String signal, int confidence, long low24, long high24, long threeLow, long threeHigh,
                   long sevenLow, long sevenHigh, int war, int sanctions, int oil, int diplomacy,
                   int currency, int economy, int trendScore, int volatilityScore, int weighted,
                   double trendPct, double volatilityPct, String explanation, String evidence, int historyCount) {
            this.signal = signal;
            this.confidence = confidence;
            this.low24 = low24;
            this.high24 = high24;
            this.threeLow = threeLow;
            this.threeHigh = threeHigh;
            this.sevenLow = sevenLow;
            this.sevenHigh = sevenHigh;
            this.war = war;
            this.sanctions = sanctions;
            this.oil = oil;
            this.diplomacy = diplomacy;
            this.currency = currency;
            this.economy = economy;
            this.trendScore = trendScore;
            this.volatilityScore = volatilityScore;
            this.weighted = weighted;
            this.trendPct = trendPct;
            this.volatilityPct = volatilityPct;
            this.explanation = explanation;
            this.evidence = evidence;
            this.historyCount = historyCount;
        }
    }
}
