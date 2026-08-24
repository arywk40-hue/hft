#!/usr/bin/env python3
"""Isolated, fail-closed runner for Phase 10 cluster-conditioned prototypes."""
from __future__ import annotations
import argparse, hashlib, json, platform
from pathlib import Path
import sys
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, precision_recall_fscore_support
from sklearn.preprocessing import StandardScaler
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from src.ebx.ml.day_clustering import day_features, deterministic_pam, representative_indices, standardize_development
from src.ebx.ml.event_features import causal_features, event_dataset
from src.ebx.ml.latency import benchmark
from src.ebx.ml.oracle_trades import extract_oracle_trades
from src.ebx.ml.prototype_strategy import simulate_confidence_strategy

AVAILABLE = tuple(range(1, 65)) + tuple(range(80, 86))
DEVELOPMENT, FINAL_TEST = AVAILABLE[:42], AVAILABLE[42:]
SOURCE_FEATURES = ["PB1_T1", "VB1_T1", "V1_T1", "PV1_T1"]

def load_day(path: Path) -> pd.DataFrame:
    columns = ["Time", "Price", *SOURCE_FEATURES]
    available = pd.read_csv(path, nrows=0).columns
    frame = pd.read_csv(path, usecols=[c for c in columns if c in available])
    if "Price" not in frame: raise ValueError(f"missing Price: {path}")
    frame["timestamp_seconds"] = pd.to_timedelta(frame.Time).dt.total_seconds().astype(int)
    if not frame.timestamp_seconds.is_monotonic_increasing or frame.timestamp_seconds.duplicated().any():
        raise ValueError(f"timestamps must be strictly increasing and day-local: {path}")
    return frame

def summarize(trades: pd.DataFrame, strategy: str) -> dict[str, object]:
    values = trades.net_return.to_numpy(float) if not trades.empty else np.array([])
    equity = np.r_[0., np.cumsum(values)]; drawdown = equity - np.maximum.accumulate(equity)
    return {"strategy": strategy, "gross_pnl": float(trades.gross_return.sum()) if len(trades) else 0.,
            "transaction_cost": float(trades.transaction_cost.sum()) if len(trades) else 0.,
            "net_pnl": float(values.sum()), "trade_count": int(len(trades)),
            "hit_rate": float((values > 0).mean()) if len(values) else 0.,
            "average_trade_return": float(values.mean()) if len(values) else 0.,
            "median_trade_return": float(np.median(values)) if len(values) else 0.,
            "turnover": float(2*trades.position_size.sum()) if len(trades) else 0.,
            "average_exposure": float(trades.position_size.mean()) if len(trades) else 0.,
            "maximum_exposure": float(trades.position_size.max()) if len(trades) else 0.,
            "max_drawdown": float(drawdown.min())}

def figures(out: Path, table: pd.DataFrame, representatives: pd.DataFrame, oracle: pd.DataFrame, trades: pd.DataFrame) -> None:
    """Small, legible audit figures; all values are from already-written artifacts."""
    import matplotlib.pyplot as plt
    root=Path("figures/ml_phase10"); root.mkdir(parents=True,exist_ok=True)
    plt.figure(figsize=(7,4)); plt.scatter(table.open_to_close_return,table.realized_vol_1s,c=table.cluster,cmap="tab10")
    plt.xlabel("open-to-close return"); plt.ylabel("1s realized volatility"); plt.tight_layout(); plt.savefig(root/"cluster_visualization.png",dpi=140); plt.close()
    plt.figure(figsize=(8,4)); equity=np.cumsum(trades.net_return.to_numpy(float)) if len(trades) else np.array([0.])
    plt.plot(equity); plt.title("Final-test equity curve"); plt.xlabel("trade"); plt.ylabel("net return"); plt.tight_layout(); plt.savefig(root/"equity_curve.png",dpi=140); plt.close()
    plt.figure(figsize=(8,4)); daily=trades.groupby("day").net_return.sum() if len(trades) else pd.Series(dtype=float)
    daily.plot(kind="bar"); plt.title("Final-test daily P&L"); plt.tight_layout(); plt.savefig(root/"daily_pnl.png",dpi=140); plt.close()
    plt.figure(figsize=(8,4)); dd=equity-np.maximum.accumulate(equity); plt.plot(dd); plt.title("Drawdown"); plt.tight_layout(); plt.savefig(root/"drawdown.png",dpi=140); plt.close()

def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--data-dir",default="data"); parser.add_argument("--output",default="results/ml/cluster_prototype")
    parser.add_argument("--run-test",action="store_true",help="Read final 28 days only after config freeze.")
    parser.add_argument("--render-figures",action="store_true",help="Render charts in an environment with a writable font cache.")
    args=parser.parse_args(); data,out=Path(args.data_dir),Path(args.output); out.mkdir(parents=True,exist_ok=True)
    missing=[d for d in AVAILABLE if not (data/f"day{d}.csv").is_file()]
    if missing: raise FileNotFoundError(f"missing permitted development files: {missing}")
    split={"available_days":list(AVAILABLE),"development_pool":list(DEVELOPMENT),"final_test_pool":list(FINAL_TEST),"missing_days":list(range(65,80)),"locked_holdout_days":list(range(86,109)),"test_read_before_config_freeze":False}
    (out/"split_manifest.json").write_text(json.dumps(split,indent=2)+"\n")
    frames={d:load_day(data/f"day{d}.csv") for d in DEVELOPMENT}
    table=pd.DataFrame([day_features(d,f) for d,f in frames.items()]); day_cols=[c for c in table if c!="day"]
    x,norm=standardize_development(table,day_cols); pam=deterministic_pam(x,5); table["cluster"]=pam.labels
    table.to_csv(out/"day_features.csv",index=False); table[["day","cluster"]].to_csv(out/"cluster_assignments.csv",index=False)
    representatives=table.iloc[representative_indices(pam.labels,pam.medoid_indices)].copy()
    representatives["is_medoid"]=representatives.index.isin(pam.medoid_indices); representatives.to_csv(out/"representative_days.csv",index=False)
    oracle=pd.concat([extract_oracle_trades(int(row.day),frames[int(row.day)]) for row in representatives.itertuples()],ignore_index=True)
    oracle=oracle.merge(table[["day","cluster"]],on="day",how="left"); oracle.to_csv(out/"oracle_trade_log.csv",index=False)
    feature_frames={d:causal_features(f,day=d,feature_columns=[c for c in SOURCE_FEATURES if c in f]) for d,f in frames.items()}
    events=event_dataset(pd.concat(feature_frames.values(),ignore_index=True),oracle)
    feature_cols=[c for c in events if c not in {"day","timestamp_seconds","label","sample_type"}]
    events[["day","timestamp_seconds","label","sample_type"]].to_csv(out/"event_dataset.csv",index=False)
    (out/"event_dataset_manifest.json").write_text(json.dumps({"positive_count":int((events.label!=0).sum()),"negative_count":int((events.label==0).sum()),"source_features":SOURCE_FEATURES,"causality":"rolling windows stop at timestamp; future prices occur only in oracle labels"},indent=2)+"\n")
    if events.empty or events.label.nunique()<2: raise RuntimeError("insufficient event labels")
    validation_days=set(DEVELOPMENT[-10:]); train=events[~events.day.isin(validation_days)]; valid=events[events.day.isin(validation_days)]
    scaler=StandardScaler().fit(train[feature_cols])
    model=LogisticRegression(max_iter=1000,class_weight="balanced",random_state=20260824).fit(scaler.transform(train[feature_cols]),train.label)
    thresholds=(.55,.60,.65,.70,.75); scores=[]
    for threshold in thresholds:
        pieces=[]
        for day in validation_days:
            f=feature_frames[day].dropna(subset=feature_cols)
            pieces.append(simulate_confidence_strategy(f,model.predict_proba(scaler.transform(f[feature_cols])),frames[day],threshold=threshold,safety_buffer=.00005,target_volatility=.0005))
        scores.append((summarize(pd.concat(pieces,ignore_index=True),"prototype")["net_pnl"],threshold))
    threshold=max(scores)[1]
    probabilities=model.predict_proba(scaler.transform(valid[feature_cols])); prediction=model.classes_[probabilities.argmax(axis=1)]
    precision,recall,_,_=precision_recall_fscore_support(valid.label!=0,prediction!=0,average="binary",zero_division=0)
    flat_index=list(model.classes_).index(0) if 0 in model.classes_ else None
    opportunity=1-probabilities[:,flat_index] if flat_index is not None else probabilities.max(axis=1)
    validation={"threshold_selected_on_inner_validation":threshold,"precision_opportunity":float(precision),"recall_opportunity":float(recall),"pr_auc_opportunity":float(average_precision_score(valid.label!=0,opportunity)),"brier":float(brier_score_loss(valid.label!=0,opportunity)),"selected_features":feature_cols}
    (out/"validation_metrics.json").write_text(json.dumps(validation,indent=2)+"\n")
    pd.DataFrame({"feature":feature_cols,"coefficient":np.abs(model.coef_).max(axis=0)}).sort_values("coefficient",ascending=False).to_csv(out/"selected_features.csv",index=False)
    config={"phase":10,"model":"balanced multinomial logistic regression","source_features":SOURCE_FEATURES,"entry_threshold":threshold,"safety_buffer":.00005,"target_volatility":.0005,"max_hold_seconds":300,"cost_bps_per_side":1,"train_days":sorted(map(int,train.day.unique())),"validation_days":sorted(validation_days),"test_days":list(FINAL_TEST),"day_normalization":norm,"frozen_before_test":True}
    encoded=json.dumps(config,sort_keys=True,indent=2)+"\n"; (out/"strategy_config.json").write_text(encoded); (out/"strategy_config.sha256").write_text(hashlib.sha256(encoded.encode()).hexdigest()+"\n")
    raw_one=valid.iloc[[0]][feature_cols]
    scaled_one=scaler.transform(raw_one)
    model_only=benchmark(lambda:model.predict_proba(scaled_one))
    model_only.update({"cpu":platform.processor(),"model":"LogisticRegression","measurement":"model_only_batch_1"})
    preprocess_model=benchmark(lambda:model.predict_proba(scaler.transform(raw_one)))
    preprocess_model.update({"cpu":platform.processor(),"model":"LogisticRegression","measurement":"preprocessing_plus_model_batch_1"})
    # Recompute one bounded causal window to include signal-side feature updates.
    latency_frame=frames[DEVELOPMENT[-1]].iloc[:601].copy()
    complete=benchmark(lambda: causal_features(latency_frame,day=DEVELOPMENT[-1],feature_columns=[c for c in SOURCE_FEATURES if c in latency_frame]).iloc[[-1]])
    complete.update({"cpu":platform.processor(),"model":"causal_feature_update","measurement":"complete_causal_feature_update_batch_1"})
    latency_rows=[model_only,preprocess_model,complete]
    pd.DataFrame(latency_rows).to_csv(out/"latency.csv",index=False); (out/"latency.json").write_text(json.dumps(latency_rows,indent=2)+"\n")
    test_metrics={"status":"not_run","reason":"run --run-test only after config review"}
    if args.run_test:
        test_frames={d:load_day(data/f"day{d}.csv") for d in FINAL_TEST}
        trades=[]
        for day,frame in test_frames.items():
            f=causal_features(frame,day=day,feature_columns=[c for c in SOURCE_FEATURES if c in frame]).dropna(subset=feature_cols)
            trades.append(simulate_confidence_strategy(f,model.predict_proba(scaler.transform(f[feature_cols])),frame,threshold=threshold,safety_buffer=.00005,target_volatility=.0005))
        trade_log=pd.concat(trades,ignore_index=True); trade_log.to_csv(out/"trade_log.csv",index=False)
        trade_log.groupby("day").net_return.sum().rename("net_pnl").reset_index().to_csv(out/"daily_pnl.csv",index=False)
        test_metrics=summarize(trade_log,"cluster_prototype")
        cost_rows=[]
        for bps in (0,1,2,5):
            adjusted=trade_log.copy(); adjusted["transaction_cost"]=2*bps/10000*adjusted.position_size
            adjusted["net_return"]=adjusted.gross_return-adjusted.transaction_cost
            cost_rows.append({"bps_per_side":bps,**summarize(adjusted,"cluster_prototype")})
        pd.DataFrame(cost_rows).to_csv(out/"cost_sensitivity.csv",index=False)
        if args.render_figures:
            figures(out,table,representatives,oracle,trade_log)
    (out/"test_metrics.json").write_text(json.dumps(test_metrics,indent=2)+"\n")
    (out/"run_manifest.json").write_text(json.dumps({"status":"partial_real_data_execution" if args.run_test else "development_complete_final_test_not_run","test_executed":args.run_test,"holdout_days_loaded":[],"figures_rendered":args.render_figures,"known_gaps":["required comparator backtests","complete figure suite","model-only and complete causal-pipeline latency"]},indent=2)+"\n")
if __name__=="__main__": main()
