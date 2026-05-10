# v0.6 方法边界说明

## 1. WBGT proxy 不是 official WBGT

v0.6 中的 WBGT proxy 使用气温、湿球温度近似、Tmrt proxy 和风速构造。它适合 hotspot prioritisation，但不能代替官方 WBGT。正式论文和 public-health wording 必须说清楚：

> WBGT proxy was used for screening and prioritisation only; official WBGT observations were reserved for calibration and validation.

## 2. Tmrt proxy 不是 SOLWEIG

v0.6 还没有建筑阴影、树冠阴影和三维辐射交换模型。它用 shortwave radiation、shade fraction、SVF proxy 和 GVI 做 screening-level Tmrt estimate。

v0.8 应改为：

```text
UMEP/SOLWEIG → Tmrt → UTCI/PET
```

## 3. Station validation 不能直接等于 grid validation

NEA 站点数据可用于 nowcast / background meteorology validation，但不能直接证明每个 50 m grid 的微气候预测准确。要验证 grid-level，需要：

```text
mobile monitoring
fixed low-cost sensor campaign
WBGT meter / globe thermometer
thermal walk protocol
```

你的 Plymouth dissertation 证明你掌握了 mobile monitoring + 120-s POI exposure window + GEMA 的方法，但它不能直接校准 Singapore heatwave model，因为它是在 Plymouth winter walking context 下完成的。

## 4. 风速是最大不确定性之一

街区风速受建筑峡谷、树冠、开口、局地湍流影响。v0.6 只能做 morphology-based reduction，不要声称精确街谷风场。

## 5. 作品集推荐表述

推荐：

> v0.6 provides a calibrated-ready forecast pipeline and hotspot-prioritisation workflow, not an operational warning system.

避免：

> v0.6 can accurately predict street-level WBGT for all Toa Payoh blocks.
