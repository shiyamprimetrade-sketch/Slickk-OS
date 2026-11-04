package online.slickk.os;

import android.app.Activity;
import android.content.Intent;
import android.content.pm.ResolveInfo;
import android.graphics.Color;
import android.os.Bundle;
import android.provider.Settings;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;

/** An offline Slickk Home UI: an unprivileged Android launcher experiment. */
public final class HomeActivity extends Activity {
  private LinearLayout body;

  @Override public void onCreate(Bundle state) {
    super.onCreate(state);
    showHome();
  }

  private int dp(int units) {
    return Math.round(units * getResources().getDisplayMetrics().density);
  }

  private void newScreen() {
    ScrollView scroll = new ScrollView(this);
    scroll.setFillViewport(true);
    scroll.setBackgroundColor(Color.rgb(246, 248, 250));
    body = new LinearLayout(this);
    body.setOrientation(LinearLayout.VERTICAL);
    body.setPadding(dp(24), dp(40), dp(24), dp(24));
    scroll.addView(body);
    setContentView(scroll);
  }

  private void heading(String text, int size) {
    TextView label = new TextView(this);
    label.setText(text);
    label.setTextSize(size);
    label.setTextColor(Color.rgb(29, 42, 60));
    label.setGravity(Gravity.START);
    label.setPadding(0, 0, 0, dp(18));
    body.addView(label);
  }

  private void button(String label, View.OnClickListener action) {
    Button b = new Button(this);
    b.setText(label);
    b.setAllCaps(false);
    b.setTextSize(17);
    b.setContentDescription(label);
    b.setMinHeight(dp(56));
    LinearLayout.LayoutParams params =
        new LinearLayout.LayoutParams(-1, dp(62));
    params.bottomMargin = dp(8);
    body.addView(b, params);
    b.setOnClickListener(action);
  }

  private void showHome() {
    newScreen();
    heading("Slickk OS", 34);
    heading("Android-compatible experience prototype", 16);
    button("All apps", view -> showApps());
    button("Settings", view -> startActivity(new Intent(Settings.ACTION_SETTINGS)));
    button("Home", view -> showHome());
  }

  private void showApps() {
    newScreen();
    heading("All apps", 28);
    button("Back to home", view -> showHome());
    Intent launcher = new Intent(Intent.ACTION_MAIN);
    launcher.addCategory(Intent.CATEGORY_LAUNCHER);
    List<ResolveInfo> apps = getPackageManager().queryIntentActivities(launcher, 0);
    Collections.sort(apps, Comparator.comparing(
        item -> String.valueOf(item.loadLabel(getPackageManager())),
        String.CASE_INSENSITIVE_ORDER));
    for (ResolveInfo app : apps) {
      if (app.activityInfo == null || getPackageName().equals(app.activityInfo.packageName)) {
        continue;
      }
      button(String.valueOf(app.loadLabel(getPackageManager())), view -> {
        Intent launch = new Intent(Intent.ACTION_MAIN);
        launch.addCategory(Intent.CATEGORY_LAUNCHER);
        launch.setClassName(app.activityInfo.packageName, app.activityInfo.name);
        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        startActivity(launch);
      });
    }
  }

  @Override public void onBackPressed() {
    showHome();
  }
}
