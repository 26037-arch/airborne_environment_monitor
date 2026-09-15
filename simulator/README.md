# Webots 공중 환경 계측 시뮬레이터

이 모듈은 추진·발사를 모델링하지 않습니다. payload는 사용자가 지정한 고도와 속도에서 시작하고, Webots가 중력과 강체 운동을 계산합니다. 환경 엔진이 항력을 위한 공기 밀도와 바람을 제공하고, 센서 모델은 기존 18열 v1 또는 Flight Controller state가 붙은 29열 v2 telemetry를 만듭니다.

## 데이터 의미

| 용어 | 이 프로젝트에서의 의미 |
|---|---|
| Weather | 특정 시각의 실제 날씨. 이 프로그램은 제공하지 않습니다. |
| Climate | 긴 기간에 걸친 기후의 통계적 특성입니다. |
| Climatology | 같은 달의 여러 시각/연도를 평균한 대표 profile입니다. ERA5 월 자료를 이 목적으로 씁니다. |
| Standard atmosphere | 실제 지역 날씨가 아닌, 고도별 온도·압력·밀도를 정의한 COESA 1976 기준 모델입니다. |
| Reanalysis | 관측과 수치모델을 결합해 과거 대기 상태를 일관된 격자로 재구성한 자료입니다. |
| Simulation | 위 자료와 명시적 가정으로 계산한 true state입니다. |
| Measurement | 실제 센서가 출력한 값입니다. 시뮬레이터 sensor reading은 측정이 아니라 센서 모사값입니다. |

ERA5 monthly means는 현재 날씨가 아닙니다. CAMS EAC4도 현장 SPS30의 국지 측정값이 아니라 전지구 대기조성 재분석의 배경 농도입니다. 도로, 굴뚝, 실내 먼지 같은 소규모 오염원과 지역 편향을 완전히 표현한다고 간주하면 안 됩니다. UI는 항상 `CLIMATOLOGY, NOT CURRENT WEATHER`와 CAMS 설치 상태를 표시합니다.

## 설치와 실행

요구사항은 Python 3.11+, Webots R2025a, 그리고 아래 Python package입니다.

```powershell
python -m pip install -r simulator/requirements.txt
python simulator/main.py
```

Control GUI의 `Flight source`는 `OFF`(v1), `MOCK`(adapter pipeline 시험용 v2), `MAVLINK`(PX4/ArduPilot state 수신) 중 선택합니다. MAVLink endpoint의 기본값은 `udp:127.0.0.1:14550`입니다. Mock은 flight-control algorithm이 아니라 환경/telemetry composition을 hardware 없이 검증하기 위한 source입니다.

Control GUI에서 값을 정하고 **Start Webots**를 누릅니다. Webots 3D 창에는 payload, 주황색 이동 궤적, true wind(청록), ground velocity(노랑), relative-air velocity(자홍) 벡터가 표시됩니다. 별도 terminal에서 기존 지상국을 그대로 실행합니다.

```powershell
cd ground_station
python main.py --simulation
```

시뮬레이션이 보내는 UDP는 Webots `Emitter → Receiver`를 통과한 뒤 localhost `127.0.0.1:19000`으로 연결됩니다. 실제 Arduino는 `python main.py`, 기록 재생은 `python main.py --replay path\telemetry.csv`입니다. 세 입력은 모두 `shared/telemetry_schema.py`의 v1/v2 parser를 사용합니다.

## 데이터 모드

- `EARTH CLIMATOLOGY`: 설치된 ERA5 profile을 사용합니다. 없거나 고도 범위 밖이면 COESA 1976으로 명시적으로 fallback합니다. CAMS가 없거나 범위 밖이면 PM은 `NA`입니다.
- `STANDARD ATMOSPHERE`: 온도·압력·밀도만 COESA 1976으로 계산합니다. 습도와 PM은 `NA`이고 CAMS를 조회하지 않습니다.
- `CUSTOM SYNTHETIC TEST`: UI의 사용자 입력만 사용하며 provenance에 `SYNTHETIC TEST DATA`를 기록합니다.

PM1과 PM4는 현재 선택한 CAMS EAC4 제품이 직접 제공하지 않으므로 추정하지 않습니다. Arduino 열은 유지하지만 값은 `NA`, `sps_ok=0`입니다. CAMS surface scalar는 그 고도 ±1 m에서만 유효하며 공중으로 임의 외삽하지 않습니다. 원본 `kg/m³`는 runtime에서 `× 1e9`하여 `µg/m³`로 변환합니다.

## 공식 원본을 오프라인 profile로 준비하기

Repository에는 실제 ERA5/CAMS 수치를 가장한 예제 profile을 넣지 않았습니다. Copernicus 포털에서 필요한 위치·기간·변수를 NetCDF로 받은 뒤, 실제 파일의 변수명과 `units` attribute를 확인해 일회성 전처리를 실행합니다. 실행 중에는 네트워크를 사용하지 않습니다.

ERA5 pressure-level 예:

```powershell
python simulator/tools/prepare_climatology.py era5 source-era5.nc `
  simulator/data/climatology/era5/seoul_sep.npz `
  --latitude 37.5 --longitude 127.0 --month 9 `
  --time-coord valid_time --level-coord pressure_level `
  --temperature-var t --rh-var r --geopotential-var z --u-var u --v-var v
```

전처리기는 geopotential을 `z / 9.80665`로 geopotential height로 바꾸고, 고도 증가·압력 감소, 온도/RH 범위, 모든 단위를 검사합니다. 변수명은 실제 파일에 따라 다를 수 있으므로 명령행에서 고칩니다.

CAMS 예:

```powershell
python simulator/tools/prepare_climatology.py cams source-cams.nc `
  simulator/data/climatology/cams/seoul_sep.npz `
  --latitude 37.5 --longitude 127.0 --month 9 `
  --pm25-var ACTUAL_PM25_NAME --pm10-var ACTUAL_PM10_NAME
```

PM 변수명은 추측하지 않도록 필수 인수입니다. `--altitude-var`가 없으면 전처리기는 scalar surface 값만 허용합니다. 직접 제공된 고도 좌표가 있는 파일에만 그 인수를 지정하십시오. 각 NPZ 옆 JSON에는 dataset URL, 원본 파일 SHA-256, 변수명, 요청/선택 grid 위치, 월, 평균 방법, 단위 변환을 저장합니다. 설치된 profile에서 ERA5 0.5°, CAMS 1.0°보다 먼 위치는 가장 가까운 파일을 억지로 재사용하지 않고 unavailable/fallback 처리합니다.

## 물리·풍장·난수

Webots 좌표는 ENU(`x=east, y=north, z=up`)입니다. 적용 항력은

```text
v_relative = v_payload_ground - v_air
F_drag = -0.5 × rho × Cd × area × |v_relative| × v_relative
```

입니다. `TRUE WIND`, `PAYLOAD GROUND VELOCITY`, `RELATIVE AIR VELOCITY`는 UI에서 분리해 표시합니다. 바람은 calm, constant, altitude layer, gust/random, ERA5 중 선택합니다. 방향은 북쪽 0°, 시계방향의 **불어가는 방향**입니다. Gust와 센서와 무선은 각각 명시적 `numpy.random.Generator`를 사용하고 같은 seed/step에서 재현됩니다.

ERA5 pressure-level horizontal `u/v`를 사용하지만 직접적인 vertical m/s가 없으면 수직풍은 0 m/s라는 모델 경계조건을 적용하고 provenance에 unavailable이라고 기록합니다. 이는 관측값으로 주장하지 않습니다.

## 센서 모델

- `IDEAL`: 가능한 true 값과 동일합니다. 원천 데이터가 없는 값은 여전히 `NA`입니다.
- `DATASHEET`: BME280, SPS30, u-blox NEO-M8 사양의 accuracy/precision 한계를 Gaussian의 ±3σ로 해석합니다. 이는 명시적 통계 가정이며 교정 성적서를 대신하지 않습니다.
- `CUSTOM`: 현재 공통 noise strength로 preset 크기를 배율 조정합니다.

BME280는 온도 ±0.5 °C, 습도 ±3 %RH, 압력 ±1 hPa를 ±3σ로 사용합니다. SPS30은 PM1/2.5에서 `±(5 µg/m³ + 5% reading)`(≤100), `±10%`(>100), PM4/10에서 `±25 µg/m³`(≤100), `±25%`(>100)를 사용합니다. GNSS preset은 NEO-M8 계열의 대표 horizontal 2.5 m, altitude 4 m, speed 0.05 m/s 값을 ±3σ로 해석합니다. 실제 모듈 설정·안테나·환경에 따라 성능이 달라집니다.

## 출력과 장애 시험

매 실행은 `simulator/runs/run_YYYY-MM-DD_HH-MM-SS/`에 다음 파일을 만듭니다.

- `telemetry.csv`: Arduino와 정확히 같은 header/순서, 1 Hz
- `truth.csv`: true 위치, 환경, 풍장, 상대공기속도
- `provenance.json`: 사용 자료와 fallback/가정
- `error_report.json`: bias, MAE, RMSE, 최대 절대오차, 유효 데이터 비율
- `status.json`: UI가 읽는 최신 true/sensor/radio 상태

MAVLink adapter는 physics loop에서 blocking하지 않도록 bounded non-blocking poll을 사용합니다. 이 저장소는 SITL state를 읽지만 arm/mode/motor command를 보내지 않습니다. HIL sensor injection과 virtual actuator→vehicle dynamics의 완전한 closed loop는 설치한 PX4/ArduPilot 및 공식 Webots vehicle integration에서 검증해야 하며, 현재 검증 완료로 표시하지 않습니다.

Radio failure test가 꺼져 있으면 loss/latency/range 설정은 무시되어 무손실·무지연입니다. 켜면 loss, latency, jitter, range를 적용합니다. GPS/BME/SPS/SD failure는 환경 true value를 바꾸지 않고 telemetry의 해당 값/flag만 바꿉니다.

## 검증

```powershell
python -m unittest discover -s ground_station/tests -v
python -m unittest discover -s simulator/tests -v
```

테스트 fixture는 loader 구조 검증용 synthetic data이며 실제 Earth 자료로 배포되지 않습니다. Scenario B의 실제 지역 차이는 사용자가 공식 원본으로 만든 둘 이상의 profile을 설치한 뒤 확인해야 합니다. Webots가 설치된 시스템에서는 `simulator/webots/worlds/earth_environment.wbt`를 열어 중력, 충돌, 궤적, Emitter/Receiver를 통합 점검하십시오.

## 출처

- U.S. Standard Atmosphere 1976: NOAA / NASA / U.S. Air Force, COESA
- ERA5 monthly averaged pressure levels: Copernicus Climate Change Service / ECMWF
- CAMS global reanalysis EAC4 monthly: Copernicus Atmosphere Monitoring Service / ECMWF
- BME280: Bosch Sensortec datasheet
- SPS30: Sensirion datasheet
- GNSS preset: u-blox NEO-M8 series documentation

정확한 URL과 provenance 필드는 [data/climatology/metadata/README.md](data/climatology/metadata/README.md)에 정리했습니다.
