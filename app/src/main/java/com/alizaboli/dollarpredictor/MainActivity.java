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
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;
import org.xmlpull.v1.XmlPullParser;
import org.xmlpull.v1.XmlPullParserFactory;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.text.NumberFormat;
import java.util.ArrayList;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class MainActivity extends Activity {
    private LinearLayout root;
    private TextView priceView, signalView, rangeView, explanationView, newsView, updatedView;
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private long currentPrice = 0;

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        buildUi();
        refresh();
    }

    private TextView text(String value, float size, boolean bold) {
        TextView t = new TextView(this);
        t.setText(value); t.setTextSize(size); t.setTextColor(Color.rgb(30,30,35));
        t.setGravity(Gravity.RIGHT); t.setPadding(24, 16, 24, 16);
        if (bold) t.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        return t;
    }

    private void buildUi() {
        ScrollView scroll = new ScrollView(this);
        root = new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL); root.setPadding(18,18,18,24);
        root.setLayoutDirection(View.LAYOUT_DIRECTION_RTL);
        scroll.addView(root); setContentView(scroll);

        TextView title = text("پیش‌بینی هوشمند دلار", 27, true);
        title.setGravity(Gravity.CENTER); root.addView(title);
        TextView sub = text("تحلیل بازار آزاد + اخبار و ریسک سیاسی/اقتصادی", 15, false);
        sub.setGravity(Gravity.CENTER); root.addView(sub);

        priceView = text("قیمت دلار\nدر حال دریافت...", 25, true); priceView.setGravity(Gravity.CENTER); root.addView(card(priceView));
        signalView = text("سیگنال: در حال تحلیل...", 20, true); root.addView(card(signalView));
        rangeView = text("بازه احتمالی ۲۴ ساعت آینده: —", 17, false); root.addView(card(rangeView));
        explanationView = text("تحلیل: —", 16, false); root.addView(card(explanationView));

        Button refresh = new Button(this); refresh.setText("به‌روزرسانی و تحلیل مجدد"); refresh.setOnClickListener(v -> refresh()); root.addView(refresh);
        updatedView = text("آخرین بروزرسانی: —", 13, false); root.addView(updatedView);

        root.addView(text("اخبار مؤثر بر بازار", 20, true));
        newsView = text("در حال دریافت اخبار...", 15, false); root.addView(card(newsView));
        TextView disclaimer = text("توجه: این برنامه پیش‌بینی احتمالی است و توصیه خرید یا فروش ارز نیست.", 13, false);
        disclaimer.setTextColor(Color.DKGRAY); root.addView(disclaimer);
    }

    private View card(View v) {
        v.setBackgroundColor(Color.rgb(245,245,247));
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(-1, -2); p.setMargins(0,8,0,8); v.setLayoutParams(p); return v;
    }

    private void refresh() {
        priceView.setText("قیمت دلار\nدر حال دریافت..."); signalView.setText("سیگنال: در حال تحلیل...");
        executor.execute(() -> {
            long price = fetchDollarPrice();
            ArrayList<String> headlines = fetchNews();
            Prediction prediction = analyze(price, headlines);
            runOnUiThread(() -> showResult(price, headlines, prediction));
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
                long p = extractPrice(html);
                if (p > 100000) return p / 10; // rial -> toman when source is IRR
                if (p > 1000) return p;
            } catch (Exception ignored) {}
        }
        return 0;
    }

    private long extractPrice(String html) {
        String[] patterns = {
                "(?i)دلار.*?([0-9]{1,3}(?:[,،][0-9]{3}){1,2})",
                "(?i)(?:sell|selling|price)[^0-9]{0,80}([0-9]{1,3}(?:[,][0-9]{3}){1,2})"
        };
        for (String s : patterns) {
            Matcher m = Pattern.compile(s, Pattern.DOTALL).matcher(html);
            if (m.find()) {
                String n = m.group(1).replace(",", "").replace("،", "");
                try { return Long.parseLong(n); } catch (Exception ignored) {}
            }
        }
        return 0;
    }

    private ArrayList<String> fetchNews() {
        ArrayList<String> out = new ArrayList<>();
        try {
            String xml = get("https://news.google.com/rss/search?q=Iran+economy+OR+Iran+war+OR+Iran+dollar&hl=en-US&gl=US&ceid=US:en");
            XmlPullParserFactory f = XmlPullParserFactory.newInstance(); XmlPullParser x = f.newPullParser();
            x.setInput(new java.io.StringReader(xml)); int event; boolean item=false; String title=null;
            while ((event=x.next()) != XmlPullParser.END_DOCUMENT && out.size()<8) {
                if (event==XmlPullParser.START_TAG && "item".equals(x.getName())) item=true;
                else if (event==XmlPullParser.END_TAG && "item".equals(x.getName())) item=false;
                else if (item && event==XmlPullParser.START_TAG && "title".equals(x.getName())) { title=x.nextText(); if(title!=null) out.add(title.trim()); }
            }
        } catch (Exception ignored) {}
        return out;
    }

    private Prediction analyze(long price, ArrayList<String> news) {
        int score=0; StringBuilder why=new StringBuilder();
        for(String h:news) {
            String s=h.toLowerCase(Locale.ROOT);
            if(s.contains("sanction")||s.contains("blockade")||s.contains("war")||s.contains("attack")||s.contains("strike")||s.contains("oil export")){score+=2; why.append("• خبر پرریسک: ").append(h).append("\n");}
            else if(s.contains("ceasefire")||s.contains("talks")||s.contains("agreement")||s.contains("deal")||s.contains("de-escalation")){score-=2; why.append("• خبر کاهنده ریسک: ").append(h).append("\n");}
        }
        String signal = score>=3 ? "احتمال افزایش 🔴" : score<=-3 ? "احتمال کاهش 🟢" : "نوسانی / نامشخص 🟡";
        long base=price>0?price:220000;
        double pct=score>=3?0.035:score<=-3?-0.025:0.012;
        long low=Math.round(base*(1-pct)), high=Math.round(base*(1+pct));
        String explanation=(score>0?"ریسک خبری فعلاً بیشتر به سمت فشار صعودی است.":score<0?"ریسک خبری فعلاً کاهش فشار را نشان می‌دهد.":"سیگنال خبری قطعی نیست و بازار می‌تواند نوسانی باشد.");
        if(why.length()==0) why.append("• خبر مشخص و قابل اتکایی با اثر مستقیم در فهرست فعلی شناسایی نشد.\n");
        return new Prediction(signal,low,high,explanation+"\n\n"+why);
    }

    private void showResult(long price, ArrayList<String> news, Prediction p) {
        currentPrice=price;
        priceView.setText(price>0?"قیمت تقریبی دلار\n"+format(price)+" تومان":"قیمت دلار\nدریافت نشد");
        signalView.setText("سیگنال ۲۴ ساعته: "+p.signal);
        rangeView.setText("بازه احتمالی ۲۴ ساعت آینده\n"+format(p.low)+" تا "+format(p.high)+" تومان");
        explanationView.setText("تحلیل\n"+p.explanation);
        StringBuilder n=new StringBuilder(); if(news.isEmpty()) n.append("خبر جدیدی دریافت نشد."); else for(int i=0;i<news.size();i++) n.append(i+1).append(". ").append(news.get(i)).append("\n\n");
        newsView.setText(n.toString());
        updatedView.setText("آخرین بروزرسانی: همین الان");
    }

    private String format(long n){return NumberFormat.getNumberInstance(Locale.US).format(n);}

    private String get(String url) throws Exception {
        HttpURLConnection c=(HttpURLConnection)new URL(url).openConnection(); c.setConnectTimeout(12000); c.setReadTimeout(15000); c.setRequestProperty("User-Agent","Mozilla/5.0"); c.setRequestMethod("GET");
        InputStream in=c.getResponseCode()<400?c.getInputStream():c.getErrorStream(); BufferedReader r=new BufferedReader(new InputStreamReader(in)); StringBuilder b=new StringBuilder(); String line; while((line=r.readLine())!=null)b.append(line).append('\n'); r.close(); c.disconnect(); return b.toString();
    }

    @Override protected void onDestroy(){super.onDestroy();executor.shutdownNow();}
    private static class Prediction { final String signal,explanation; final long low,high; Prediction(String s,long l,long h,String e){signal=s;low=l;high=h;explanation=e;} }
}
