# Dataset provenance

## Runtime 자료

각 `era5/*.npz`, `cams/*.npz`에는 같은 stem의 `.json`이 반드시 있어야 합니다. loader는 JSON이 없는 profile을 설치된 데이터로 간주하지 않습니다. JSON은 최소 `latitude`, `longitude`, `month`를 포함하고 전처리기는 다음을 추가합니다.

```text
dataset / provider / dataset_url
input_file / input_sha256
selected grid latitude / longitude / month
averaging method
source variable names and units
height/unit conversion
available and unavailable quantities
```

## 기준 출처

- U.S. Standard Atmosphere 1976 (NASA): https://ntrs.nasa.gov/archive/nasa/casi.ntrs.nasa.gov/19770009539.pdf
- U.S. Standard Atmosphere 1976 (NOAA): https://www.ngdc.noaa.gov/stp/space-weather/online-publications/miscellaneous/us-standard-atmosphere-1976/us-standard-atmosphere_st76-1562_noaa.pdf
- ERA5 pressure-level monthly means: https://cds.climate.copernicus.eu/datasets/reanalysis-era5-pressure-levels-monthly-means
- ERA5 documentation: https://confluence.ecmwf.int/pages/viewpage.action?pageId=414588701
- CAMS EAC4 monthly: https://ads.atmosphere.copernicus.eu/datasets/cams-global-reanalysis-eac4-monthly
- BME280 datasheet: https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bme280-ds002.pdf
- SPS30 datasheet: https://sensirion.com/file/datasheet_sps30
- u-blox NEO-M8 series: https://www.u-blox.com/en/product/neo-m8-series
- Webots coordinate system / APIs: https://cyberbotics.com/doc/reference/index

## 제한과 금지 사항

- 월평균 climatology를 현재 날씨라고 부르지 않습니다.
- CAMS background를 현장 SPS30 측정과 동일하다고 부르지 않습니다.
- PM1/PM4와 지원 범위 밖의 고도값을 추정하지 않습니다.
- 원본 file hash가 달라지면 새 provenance JSON을 생성합니다.
- 테스트의 synthetic fixture를 `simulator/data/`에 복사하지 않습니다.
