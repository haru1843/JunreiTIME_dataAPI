# APIの概要

ドラマやアニメにゆかりのある土地の情報を取得するためのAPIです.

## 各機能の名称とリンク
+ [ランダム取得](#random_locations-get)
+ [範囲内取得](#locations_in_circle-get)
+ [予算内取得](#locations_within_budget-get)

## TOC

<!-- @import "[TOC]" {cmd="toc" depthFrom=1 depthTo=6 orderedList=false} -->

<!-- code_chunk_output -->

- [APIの仕様](#apiの仕様)
  - [/random_locations [GET]](#random_locations-get)
    - [概要](#概要)
    - [パラメータ](#パラメータ)
    - [返却値](#返却値)
    - [利用例](#利用例)
  - [/locations_in_circle [GET]](#locations_in_circle-get)
    - [概要](#概要-1)
    - [パラメータ](#パラメータ-1)
    - [返却値](#返却値-1)
    - [利用例](#利用例-1)
  - [/locations_within_budget [GET]](#locations_within_budget-get)
    - [概要](#概要-2)
    - [パラメータ](#パラメータ-2)
    - [返却値](#返却値-2)
    - [利用例](#利用例-2)

<!-- /code_chunk_output -->


# APIの仕様

ホスト : `https://junrei-time-dataapi.herokuapp.com/api/`

## /random_locations [GET]

### 概要

ランダムに土地情報を取得する

### パラメータ

| パラメータ名 | 必須 |            概要            | 型名 | デフォルト | 値域              | 備考 |
|:------------:|:----:|:--------------------------:|------|------------|-------------------|------|
|     num      |      | いくつのデータを取得するか | int  | `10`       | `0 < num <= 1000` |      |

各パラメータにおいて, 値域を満たさない場合, `400 BadRequest` が返却される

### 返却値

下記の土地情報のオブジェクトがリストになったJSON形式のデータが返ってきます.

|          key          |        valueの内容         | valueの型 |
|:---------------------:|:--------------------------:|:---------:|
|       `"code"`        |          住所番号          |    str    |
|        `"lat"`        |            緯度            |   float   |
|        `"lon"`        |            経度            |   float   |
|       `"name"`        |        住所テキスト        |    str    |
|   `"orignal_name"`    |      元の住所テキスト      |    str    |
| `"scene_in_the_work"` |     作中での登場シーン     |    str    |
|        `"tag"`        | アニメかドラマかの判別タグ |    str    |
|       `"title"`       |           作品名           |    str    |

### 利用例

```
https://junrei-time-dataapi.herokuapp.com/api/random_locations
https://junrei-time-dataapi.herokuapp.com/api/random_locations?num=3
```

## /locations_in_circle [GET]

### 概要

中心点(`lat`, `lon`)から半径`r`内の円にある関連地を取得します.

### パラメータ


| パラメータ名 | 必須 |                           概要                           | 型名  | デフォルト    | 値域                              | 備考                |
|:------------:|:----:|:--------------------------------------------------------:|-------|---------------|-----------------------------------|---------------------|
|     lat      |  ✓   |             中心地の緯度(北極=90, 南極=-90)              | float |               | `-90.0 <= lat <= 90`              | 0は赤道             |
|     lon      |  ✓   |                中心地の経度(東→正, 西→負)                | float |               | `-180.0 <= lon <= 180.0`          | -180と180は同じ地点 |
|      r       |  ✓   |             中心地からの対象半径(単位は`m`)              | int   |               | `100 <= r <= 100000`              |                     |
|     tag      |      | 選択対象を`anime`か`drama`, もしくはその両方を選択できる | str   | "anime,drama" | `"anime", "drama", "anime,drama"` |                     |
|    limit     |      | 取得個数を制限する. 制限時は距離の近いものが取得される.  | int   | 1000          | `0 < limit`                       |                     |

各パラメータにおいて, 値域を満たさない場合, `400 BadRequest` が返却される

### 返却値


#### 全体

```
responce
    ├convert
    │   ├budget
    │   └distance
    │
    ├count
    │   ├limit
    │   └total
    │
    └items : LIST[LocationObject]
```

| key                       |          valueの内容           | valueの型 |
|:--------------------------|:------------------------------:|:---------:|
| `"count"`                 |            住所番号            |           |
| ├`"limit"`                |           取得上限数           |    int    |
| └`"total"`                |         実際の総hit数          |    int    |
|                           |                                |           |
| `"items"`                 |       関連地情報のリスト       |           |
| └`"LIST[LocationObject]"` | `"LocationObject"`の内容は後述 |           |


#### LocatoinObject

```
LocationObject
    ├code
    ├distance
    ├lat
    ├lon
    ├name
    ├orignal_name
    ├scene_in_the_work
    ├tag
    └title
```

|          key          |        valueの内容         | valueの型 |
|:---------------------:|:--------------------------:|:---------:|
|       `"code"`        |          住所番号          |    str    |
|     `"distance"`      |      二点間の距離 [m]      |    int    |
|        `"lat"`        |            緯度            |   float   |
|        `"lon"`        |            経度            |   float   |
|       `"name"`        |        住所テキスト        |    str    |
|   `"orignal_name"`    |      元の住所テキスト      |    str    |
| `"scene_in_the_work"` |     作中での登場シーン     |    str    |
|        `"tag"`        | アニメかドラマかの判別タグ |    str    |
|       `"title"`       |           作品名           |    str    |

### 利用例

```
https://junrei-time-dataapi.herokuapp.com/api/locations_in_circle?lat=35.556243&lon=139.662233&r=10000&limit=10&tag=anime
```

## /locations_within_budget [GET]

### 概要

中心点(`lat`, `lon`)から, 予算`budget`で行けそうな範囲内にある関連地を取得します.

### パラメータ

| パラメータ名 | 必須 |                           概要                           | 型名  | デフォルト    | 値域                              | 備考                |
|:------------:|:----:|:--------------------------------------------------------:|-------|---------------|-----------------------------------|---------------------|
|    `lat`     |  ✓   |             中心地の緯度(北極=90, 南極=-90)              | float |               | `-90.0 <= lat <= 90`              | 0は赤道             |
|    `lon`     |  ✓   |                中心地の経度(東→正, 西→負)                | float |               | `-180.0 <= lon <= 180.0`          | -180と180は同じ地点 |
|   `budget`   |  ✓   |                        予算(片道)                        | int   |               | `10 <= budget <= 10000`           |                     |
| `func_type`  |      |               距離予測するための関数の種類               | str   | `d2`          |                                   | 詳細は後述          |
|    `tag`     |      | 選択対象を`anime`か`drama`, もしくはその両方を選択できる | str   | `anime,drama` | `"anime", "drama", "anime,drama"` |                     |
|   `limit`    |      | 取得個数を制限する. 制限時は距離の近いものが取得される.  | int   | `1000`        | `0 < limit`                       |                     |

各パラメータにおいて, 値域を満たさない場合, `400 BadRequest` が返却される

### 返却値

#### 全体

```
responce
    ├convert
    │   ├budget
    │   └distance
    │
    ├count
    │   ├limit
    │   └total
    │
    └items : LIST[LocationObject]
```

| key                       |          valueの内容           | valueの型 |
|:--------------------------|:------------------------------:|:---------:|
| `"convert"`               |      金額→距離の変換情報       |           |
| ├`"budget"`               |              金額              |    int    |
| └`"distance"`             |          変換後の距離          |   float   |
|                           |                                |           |
| `"count"`                 |            住所番号            |           |
| ├`"limit"`                |           取得上限数           |    int    |
| └`"total"`                |         実際の総hit数          |    int    |
|                           |                                |           |
| `"items"`                 |       関連地情報のリスト       |           |
| └`"LIST[LocationObject]"` | `"LocationObject"`の内容は後述 |           |


#### LocatoinObject

```
LocationObject
    ├code
    ├distance
    ├lat
    ├lon
    ├name
    ├orignal_name
    ├scene_in_the_work
    ├tag
    └title
```

|          key          |        valueの内容         | valueの型 |
|:---------------------:|:--------------------------:|:---------:|
|       `"code"`        |          住所番号          |    str    |
|     `"distance"`      |      二点間の距離 [m]      |    int    |
|        `"lat"`        |            緯度            |   float   |
|        `"lon"`        |            経度            |   float   |
|       `"name"`        |        住所テキスト        |    str    |
|   `"orignal_name"`    |      元の住所テキスト      |    str    |
| `"scene_in_the_work"` |     作中での登場シーン     |    str    |
|        `"tag"`        | アニメかドラマかの判別タグ |    str    |
|       `"title"`       |           作品名           |    str    |

### func_typeについて

現状対応している`func_type`は以下の通りである.

| `func_type` |              内容               |                備考                |
|:-----------:|:-------------------------------:|:----------------------------------:|
|    `d1`     | 1次関数でフィッティングしたもの |                                    |
|    `d2`     | 2次関数でフィッティングしたもの |          一番良い気がする          |
|    `d3`     | 3次関数でフィッティングしたもの | 正直使いづらいのでおすすめしません |

### 利用例

```
https://junrei-time-dataapi.herokuapp.com/api/locations_within_budget?lat=35.556243&lon=139.662233&budget=300&limit=10&tag=anime&func_type=d2
```
