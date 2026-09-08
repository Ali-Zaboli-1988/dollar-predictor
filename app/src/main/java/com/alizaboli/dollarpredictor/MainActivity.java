package com.alizaboli.dollarpredictor;

import android.app.Activity;
import android.graphics.Color;
import android.graphics.Typeface;
import android.os.Bundle;
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
    private TextView priceView;
    private TextView signalView;
    private TextView rangeView;
    private TextView factorsView;
    private TextView historyView;
    private TextView validationView;
    private TextView scenariosView;
    private TextView explanationView;
    private TextView newsView;
    private TextView updatedView;
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final PredictionEngine predictionEngine = new PredictionEngine();

    @Override
    public void onCreate(Bundle savedInstanceState) {
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

        TextView sub = text(
                "تحلیل بازار آزاد + روند تاریخی + رژیم بازار + جنگ + تحریم + نفت + سیاست + اخبار",
                15,
                false);
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

        validationView = text("اعتبارسنجی روند\nدر حال محاسبه...", 16, false);
        root.addView(card(validationView));

        scenariosView = text("سناریوها\n—", 16, false);
        root.addView(card(scenariosView));

        explanationView = text("تحلیل مدل: —", 16, false);
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

        TextView disclaimer = text(
                "توجه: این برنامه یک مدل احتمالی است و توصیه خرید یا فروش ارز نیست. درصد اطمینان، اطمینان مدل به جهت حرکت است و احتمال قطعی وقوع را تضمین نمی‌کند. اعتبارسنجی نمایش‌داده‌شده فقط مؤلفه روند قیمت را می‌سنجد و به‌تنهایی اعتبار پیش‌بینی خبری را ثابت نمی‌کند.",
                13,
                false);
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
        rangeView.setText("بازه احتمالی ۲۴ ساعت آینده: —");
        factorsView.setText("عوامل مؤثر\nدر حال محاسبه...");
        historyView.setText("روند تاریخی\nدر حال دریافت داده...");
        validationView.setText("اعتبارسنجی روند\nدر حال محاسبه...");
        scenariosView.setText("سناریوها\nدر حال محاسبه...");
        explanationView.setText("تحلیل مدل: در حال محاسبه...");
        newsView.setText("در حال دریافت اخبار...");

        executor.execute(() -> {
            long price = fetchDollarPrice();
            ArrayList<String> headlines = fetchNews();
            ArrayList<Long> history = fetchHistoricalCloses();
            PredictionResult prediction = predictionEngine.predict(history, headlines);
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
            } catch (Exception ignored) {
            }
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
                try {
                    return Long.parseLong(n);
                } catch (Exception ignored) {
                }
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
                String normalized = normalizeDigits(raw)
                        .replaceAll("<[^>]+>", " ")
                        .replaceAll("&nbsp;", " ")
                        .replaceAll("\\s+", " ");
                Pattern row = Pattern.compile(
                        "([0-9]{1,3}(?:,[0-9]{3}){1,2})\\s+" +
                        "([0-9]{1,3}(?:,[0-9]{3}){1,2})\\s+" +
                        "([0-9]{1,3}(?:,[0-9]{3}){1,2})\\s+" +
                        "([0-9]{1,3}(?:,[0-9]{3}){1,2})\\s+" +
                        "(?:[-0-9.,%]+)\\s+" +
                        "(?:[0-9./-]+)");
                Matcher m = row.matcher(normalized);
                while (m.find() && closes.size() < 75) {
                    String close = m.group(4).replace(",", "");
                    try {
                        long value = Long.parseLong(close);
                        if (value > 100000) value /= 10;
                        if (value >= 10000 && value <= 1000000) closes.add(value);
                    } catch (Exception ignored) {
                    }
                }
                if (closes.size() >= 8) return closes;
                closes.clear();
            } catch (Exception ignored) {
            }
        }
        return closes;
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
                    if (event == XmlPullParser.START_TAG && "item".equals(x.getName())) {
                        item = true;
                    } else if (event == XmlPullParser.END_TAG && "item".equals(x.getName())) {
                        item = false;
                    } else if (item && event == XmlPullParser.START_TAG && "title".equals(x.getName())) {
                        String title = x.nextText();
                        if (title != null) {
                            title = title.trim();
                            String key = title.toLowerCase(Locale.ROOT).replaceAll("\\s+", " ");
                            if (!key.isEmpty() && seen.add(key)) out.add(title);
                        }
                    }
                }
            } catch (Exception ignored) {
            }
        }
        return out;
    }

    private void showResult(long price, ArrayList<Long> history, ArrayList<String> news, PredictionResult p) {
        long base = price > 0 ? price : (history.isEmpty() ? 0 : history.get(0));

        if (base > 0) {
            priceView.setText("قیمت تقریبی دلار\n" + format(base) + " تومان");
        } else {
            priceView.setText("قیمت دلار\nدریافت نشد");
        }

        signalView.setText(
                "سیگنال ۲۴ ساعته: " + directionLabel(p.direction) +
                "\nاطمینان مدل: " + p.confidence + "%" +
                "\nریسک: " + riskLabel(p.riskLevel) +
                "\nرژیم بازار: " + regimeLabel(p.regime));

        double dailyMove = p.volatilityPct > 0
                ? Math.min(0.08, Math.max(0.012, p.volatilityPct * 1.15 / 100.0))
                : 0.018;
        double directionBias = p.direction == PredictionResult.Direction.UP ? 0.35
                : p.direction == PredictionResult.Direction.DOWN ? -0.35 : 0.0;
        double lowFactor = 1.0 - dailyMove * (0.80 + Math.max(0.0, -directionBias));
        double highFactor = 1.0 + dailyMove * (0.80 + Math.max(0.0, directionBias));
        if (p.regime == MarketRegime.Type.SHOCK) {
            lowFactor = 1.0 - dailyMove * 1.45;
            highFactor = 1.0 + dailyMove * 1.45;
        } else if (p.regime == MarketRegime.Type.VOLATILE) {
            lowFactor = 1.0 - dailyMove * 1.15;
            highFactor = 1.0 + dailyMove * 1.15;
        }
        if (base > 0) {
            long low = Math.max(0L, Math.round(base * lowFactor));
            long high = Math.max(low, Math.round(base * highFactor));
            rangeView.setText("بازه احتمالی ۲۴ ساعت آینده\n" + format(low) + " تا " + format(high) + " تومان");
        } else {
            rangeView.setText("بازه احتمالی ۲۴ ساعت آینده\nبه علت نبود قیمت پایه محاسبه نشد");
        }

        StringBuilder factors = new StringBuilder("عوامل واردشده به موتور پیش‌بینی\n");
        if (p.factors.isEmpty()) {
            factors.append("سیگنال عامل مشخصی وجود ندارد.");
        } else {
            for (String factor : p.factors) factors.append("• ").append(factor).append("\n");
        }
        factors.append("\nامتیاز ترکیبی موتور: ").append(p.score);
        factorsView.setText(factors.toString());

        historyView.setText(
                "روند تاریخی دلار\n" +
                "تعداد رکورد: " + history.size() + "\n" +
                "روند ۱۰ روزه تقریبی: " + signedPercent(p.trendPct) + "\n" +
                "نوسان روزانه: " + formatPercent(p.volatilityPct) + "\n" +
                "وضعیت بازار: " + regimeLabel(p.regime));

        validationView.setText(
                "اعتبارسنجی تاریخی مؤلفه روند\n" +
                "نمونه‌های قابل ارزیابی: " + p.backtestSamples + "\n" +
                "دقت جهت روند: " + formatPercent(p.backtestAccuracy) + "\n" +
                "این عدد فقط برای مؤلفه روند قیمت است و اعتبار خبرها را اثبات نمی‌کند.");

        long scenario24 = base > 0 ? Math.round(base * dailyMove) : 0;
        long scenario3d = base > 0 ? Math.round(base * Math.min(0.16, dailyMove * 1.75)) : 0;
        long scenario7d = base > 0 ? Math.round(base * Math.min(0.28, dailyMove * 2.7)) : 0;
        if (base > 0) {
            scenariosView.setText(
                    "سناریوهای قیمتی\n\n" +
                    "۲۴ ساعت: " + format(Math.max(0, base - scenario24)) + " تا " + format(base + scenario24) + "\n" +
                    "۳ روز: " + format(Math.max(0, base - scenario3d)) + " تا " + format(base + scenario3d) + "\n" +
                    "۷ روز: " + format(Math.max(0, base - scenario7d)) + " تا " + format(base + scenario7d) + "\n\n" +
                    "سناریوی پایه: تداوم وضعیت فعلی\n" +
                    "سناریوی صعودی: تشدید فشارهای تورمی/سیاسی و افزایش تقاضا\n" +
                    "سناریوی کاهشی: کاهش تنش یا افزایش عرضه ارز");
        } else {
            scenariosView.setText("سناریوهای قیمتی\nقیمت پایه برای محاسبه در دسترس نیست.");
        }

        StringBuilder explanation = new StringBuilder("تحلیل موتور\n");
        explanation.append("جهت خروجی: ").append(directionLabel(p.direction)).append("\n");
        explanation.append("سطح ریسک: ").append(riskLabel(p.riskLevel)).append("\n");
        explanation.append("امتیاز ترکیبی: ").append(p.score).append("\n");
        explanation.append("رژیم بازار: ").append(regimeLabel(p.regime)).append("\n\n");
        if (p.factors.isEmpty()) {
            explanation.append("موتور عامل خبری/قیمتی معناداری برای تقویت جهت پیدا نکرد.");
        } else {
            explanation.append("موتور چند سیگنال را با هم ترکیب کرده و در صورت تعارض، خروجی را به NEUTRAL نزدیک می‌کند.");
        }
        explanationView.setText(explanation.toString());

        StringBuilder n = new StringBuilder();
        if (news.isEmpty()) {
            n.append("خبر جدیدی دریافت نشد.");
        } else {
            for (int i = 0; i < news.size(); i++) {
                n.append(i + 1).append(". ").append(news.get(i)).append("\n\n");
            }
        }
        newsView.setText(n.toString());
        updatedView.setText("آخرین بروزرسانی: همین الان | " + news.size() + " خبر | " + history.size() + " رکورد تاریخی");
    }

    private String directionLabel(PredictionResult.Direction direction) {
        switch (direction) {
            case UP: return "احتمال افزایش 🔴";
            case DOWN: return "احتمال کاهش 🟢";
            default: return "خنثی / نامشخص 🟡";
        }
    }

    private String riskLabel(PredictionResult.RiskLevel risk) {
        switch (risk) {
            case HIGH: return "زیاد";
            case MEDIUM: return "متوسط";
            default: return "کم";
        }
    }

    private String regimeLabel(MarketRegime.Type type) {
        if (type == null) return "نامشخص";
        switch (type) {
            case SHOCK: return "شوک / بحران قیمتی";
            case VOLATILE: return "پرنوسان";
            case TRENDING: return "رونددار";
            default: return "نسبتاً آرام";
        }
    }

    private String signedPercent(double value) {
        return (value > 0 ? "+" : "") + String.format(Locale.US, "%.2f%%", value);
    }

    private String formatPercent(double value) {
        return String.format(Locale.US, "%.2f%%", value);
    }

    private String format(long value) {
        return NumberFormat.getNumberInstance(Locale.US).format(value);
    }

    private String normalizeDigits(String value) {
        if (value == null) return "";
        return value
                .replace('۰', '0').replace('۱', '1').replace('۲', '2').replace('۳', '3').replace('۴', '4')
                .replace('۵', '5').replace('۶', '6').replace('۷', '7').replace('۸', '8').replace('۹', '9');
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

    @Override
    protected void onDestroy() {
        super.onDestroy();
        executor.shutdownNow();
    }
}
