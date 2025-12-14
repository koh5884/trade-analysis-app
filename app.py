# トレード分析アプリ - Streamlit メイン

import streamlit as st
import pandas as pd
import os

# ===== モジュールインポート =====
from modules.notion_sync import sync_all_databases
from modules.data_loader import (
    load_trade_data,
    calculate_unrealized_pnl,
    get_all_trades_with_status,
)
from modules.kpi import (
    calculate_kpis,
    calculate_equity_curve,
    get_trade_summary_table,
)
from modules.charts import (
    plot_pnl_bar,
    plot_equity_curve,
    plot_win_loss_distribution,
)
from modules.trade_plot import plot_trade_chart

# ===== 設定インポート =====
import config


# ===== ページ設定 =====
st.set_page_config(
    page_title="トレード分析アプリ",
    page_icon="📈",
    layout="wide",
)


def main():
    # ===== タイトル =====
    st.title("📈 トレード分析アプリ")
    st.markdown("---")

    # ===== サイドバー =====
    with st.sidebar:
        st.header("⚙️ 設定")

        # Notion同期ボタン
        if st.button("🔄 Notion → GitHub 同期", use_container_width=True):
            with st.spinner("同期中..."):
                try:
                    sync_all_databases(
                        config.NOTION_TOKEN,
                        config.DATABASE_IDS,
                        config.GITHUB_TOKEN,
                        config.GITHUB_REPO,
                        config.GITHUB_BRANCH,
                        config.DATA_DIR,
                    )
                    st.success("✅ 同期完了!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 同期エラー: {e}")

        st.markdown("---")

        # 表示モード
        view_mode = st.radio(
            "表示モード",
            ["📊 総合サマリー", "📈 個別トレード"],
            label_visibility="collapsed",
        )

        st.markdown("---")

        # 市場選択
        market = st.selectbox("市場", ["日本", "米国"], index=0)
        market_key = "japan" if market == "日本" else "us"

        # 投資スタイル
        style = st.selectbox("投資スタイル", ["スイング", "長期"], index=0)
        style_key = "swing" if style == "スイング" else "long"

    # ===== データ読み込み =====
    df = load_trade_data(config.DATA_DIR, market_key, style_key)

    if df.empty:
        st.warning("⚠️ データがありません。Notion同期を実行してください。")
        return

    # 保有中含み損益
    unrealized_df = calculate_unrealized_pnl(df, market_key)

    # KPI計算
    capital = config.CAPITAL[market_key]
    kpis = calculate_kpis(df, unrealized_df, capital)

    # =================================================================
    # ======================= 📊 総合サマリー ==========================
    # =================================================================
    if view_mode == "📊 総合サマリー":
        st.header("📊 総合サマリー")

        currency = "¥" if market_key == "japan" else "$"

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("トレード数", f"{kpis['トレード数']}回")
        col2.metric("勝率", f"{kpis['勝率']:.1f}%")
        col3.metric("平均利益率", f"{kpis['平均利益率']:.2f}%")
        col4.metric("平均損失率", f"{kpis['平均損失率']:.2f}%")
        col5.metric("総損益", f"{currency}{kpis['総損益']:,.2f}")

        st.markdown("---")

        col6, col7, col8 = st.columns(3)
        col6.metric("元本", f"{currency}{kpis['元本']:,.2f}")
        col7.metric("実現損益", f"{currency}{kpis['実現損益']:,.2f}")
        col8.metric("保有中含み益", f"{currency}{kpis['保有中含み益']:,.2f}")

        st.markdown("---")

        tab1, tab2, tab3 = st.tabs(["💹 損益棒グラフ", "📈 資金推移", "🍰 勝敗分布"])

        with tab1:
            st.subheader("トレード別損益")
            st.pyplot(plot_pnl_bar(df, market_key))

        with tab2:
            st.subheader("資金推移")
            equity_df = calculate_equity_curve(df, unrealized_df, capital)
            st.pyplot(plot_equity_curve(equity_df, market_key))

        with tab3:
            st.subheader("勝敗分布")
            st.pyplot(plot_win_loss_distribution(df))

    # =================================================================
    # ======================= 📈 個別トレード ==========================
    # =================================================================
    elif view_mode == "📈 個別トレード":
        st.header("📈 個別トレード結果")

        summary_table = get_trade_summary_table(df, unrealized_df)

        if summary_table.empty:
            st.warning("⚠️ トレードデータがありません")
            return

        col_table, col_chart = st.columns([1.2, 2.0])

        with col_table:
            st.subheader("📋 トレード一覧（クリックで選択）")

            event = st.dataframe(
                summary_table,
                use_container_width=True,
                hide_index=True,
                selection_mode="single-row",
                on_select="rerun",
            )

            if not event.selection.rows:
                st.info("👆 上の表からトレードを選択してください")
                return

            selected_summary = summary_table.iloc[event.selection.rows[0]]

        with col_chart:
            ticker_code = selected_summary["証券コード"]
            buy_date = pd.to_datetime(selected_summary["買付日"])

            trade_row = df[
                (df["証券コード"] == ticker_code)
                & (df["買付日"] == buy_date)
            ].iloc[0]

            st.subheader(f"📊 {selected_summary['銘柄名']} ({ticker_code})")

            col1, col2, col3 = st.columns(3)
            col1.metric("ステータス", selected_summary["ステータス"])
            col2.metric(
                "損益",
                f"{'¥' if market_key == 'japan' else '$'}{selected_summary['損益']:,.0f}",
            )
            col3.metric("増減率", selected_summary["増減率"])

            st.markdown("---")

            with st.spinner("チャート読み込み中..."):
                st.pyplot(
                    plot_trade_chart(
                        trade_row,
                        market_key,
                        lookback_days=20,
                    )
                )


if __name__ == "__main__":
    main()
