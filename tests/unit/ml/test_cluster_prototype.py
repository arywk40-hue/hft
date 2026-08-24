import numpy as np
import pandas as pd
import pytest

from src.ebx.ml.day_clustering import deterministic_pam
from src.ebx.ml.oracle_trades import OracleConfig, extract_oracle_trades
from src.ebx.ml.prototype_strategy import position_size, should_enter
from src.ebx.ml.event_features import causal_features, event_dataset

def test_pam_is_deterministic_and_medoids_are_observed():
    x=np.array([[0.,0.],[0.,1.],[9.,9.],[9.,10.]])
    a=deterministic_pam(x,2); b=deterministic_pam(x,2)
    np.testing.assert_array_equal(a.labels,b.labels); np.testing.assert_array_equal(a.medoid_indices,b.medoid_indices)

def test_oracle_limits_cost_and_nonoverlap():
    frame=pd.DataFrame({"timestamp_seconds":np.arange(400),"Price":np.r_[np.linspace(100,101,200),np.linspace(101,99,200)]})
    out=extract_oracle_trades(1,frame,OracleConfig(max_trades=5,min_holding_seconds=30,max_holding_seconds=300))
    assert len(out)<=5
    assert (out.transaction_cost == .0002).all()
    assert (out.exit_timestamp_seconds.iloc[:-1].to_numpy() <= out.entry_timestamp_seconds.iloc[1:].to_numpy()).all()

def test_confidence_sizing_boundaries():
    assert position_size(.6,.01,threshold=.7,target_volatility=.01)==0
    assert position_size(1,.000001,threshold=.7,target_volatility=.01)==1
    assert should_enter(.00031,.8,threshold=.7,safety_buffer=.0001)
    assert not should_enter(.00029,.8,threshold=.7,safety_buffer=.0001)
    with pytest.raises(ValueError): position_size(1.1,.1,threshold=.7,target_volatility=.01)

def test_causal_features_do_not_change_when_future_is_changed():
    frame=pd.DataFrame({"timestamp_seconds":np.arange(700),"Price":100+np.arange(700)*.01,"PB1_T1":np.arange(700,dtype=float)})
    before=causal_features(frame,day=1,feature_columns=["PB1_T1"])
    changed=frame.copy(); changed.loc[600:,"Price"]*=5; changed.loc[600:,"PB1_T1"]*=5
    after=causal_features(changed,day=1,feature_columns=["PB1_T1"])
    pd.testing.assert_frame_equal(before.iloc[:500],after.iloc[:500])
