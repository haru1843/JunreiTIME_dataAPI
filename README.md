# APIの概要

ドラマやアニメにゆかりのある土地の情報を取得するためのAPIです.

## 各機能の名称とリンク
+ 関連地情報取得系
  + [ランダム取得](#random_locations-get)
  + [範囲内取得](#locations_in_circle-get)
  + [予算内取得](#locations_within_budget-get)
+ 作品名取得系
  + [全ての作品名を取得](#titleall-get)
  + [作品名を前方一致にて取得](#titlesearchstartswith-get)
  + [作品名を部分一致にて取得](#titlesearchcontains-get)

## Table Of Contents


<!-- @import "[TOC]" {cmd="toc" depthFrom=1 depthTo=2 orderedList=false} -->

<!-- code_chunk_output -->

- [APIの概要](#apiの概要)
  - [各機能の名称とリンク](#各機能の名称とリンク)
  - [Table Of Contents](#table-of-contents)
- [関連地取得系](#関連地取得系)
  - [/random_locations [GET]](#random_locations-get)
  - [/locations/circle [GET]](#locationscircle-get)
  - [/locations/budget [GET]](#locationsbudget-get)
  - [/locations/title [GET]](#locationstitle-get)
  - [データオブジェクトについて](#データオブジェクトについて)
- [作品タイトル関係](#作品タイトル関係)
  - [/title/all [GET]](#titleall-get)
  - [/title/search/startswith [GET]](#titlesearchstartswith-get)
  - [/title/search/contains [GET]](#titlesearchcontains-get)
  - [データオブジェクトについて](#データオブジェクトについて-1)

<!-- /code_chunk_output -->


# 関連地取得系

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

## /locations/circle [GET]

### 概要

中心点(`lat`, `lon`)から半径`r`内の円にある関連地を取得します.

### パラメータ


|  パラメータ名  | 必須 |                              概要                               | 型名  | デフォルト    | 値域                                      | 備考                          |
|:--------------:|:----:|:---------------------------------------------------------------:|-------|---------------|-------------------------------------------|-------------------------------|
|     `lat`      |  ✓   |                 中心地の緯度(北極=90, 南極=-90)                 | float |               | `-90.0 <= lat <= 90`                      | 0は赤道                       |
|     `lon`      |  ✓   |                   中心地の経度(東→正, 西→負)                    | float |               | `-180.0 <= lon <= 180.0`                  | -180と180は同じ地点           |
|      `r`       |  ✓   |                 中心地からの対象半径(単位は`m`)                 | int   |               | `0 <= r <= 500000`                        |                               |
|     `tag`      |      |    選択対象を`anime`か`drama`, もしくはその両方を選択できる     | str   | "anime,drama" | `"anime", "drama", "anime,drama"`         |                               |
|    `limit`     |      |     取得個数を制限する. 制限時は距離の近いものが取得される.     | int   | 1000          | `0 < limit`                               |                               |
|   `no_check`   |      | 関連地算出の際, 細かいチェックを行わず, 一部を概算で計算します. | str   | `"false"`     | `"true"`, `"false"`などのそれっぽい文字列 | `&no_check`だと`true`扱い     |
| `no_clustered` |      |           関連地算出の際, クラスタ構造を利用しません.           | str   | `"false"`     | `"true"`, `"false"`などのそれっぽい文字列 | `&no_clustered`だと`true`扱い |

各パラメータにおいて, 値域を満たさない場合, `400 BadRequest` が返却される

### 返却値


#### 全体

```
responce
    ├cluster
    │   ├main_cluster
    │   │   ├all
    │   │   ├inner
    │   │   ├outer
    │   │   └touch
    │   │       ├have_no_subcluster
    │   │       └have_subclusters
    │   │   
    │   └sub_cluster
    │       ├all
    │       ├inner
    │       ├outer
    │       └touch
    │
    ├count
    │   ├limit
    │   └total
    │
    ├items : LIST[LocationObject]
    │
    ├no_check
    │   ├enable
    │   └(missed_check)
    │
    ├no_clustered
    │   └enable
    │
    ├processing_time
    │
    └tag : List
```

| key                          |                    valueの内容                    | valueの型 |
|:-----------------------------|:-------------------------------------------------:|:---------:|
| `"cluster"`                  |                   クラスタ情報                    |           |
| ├`"main_cluster"`            |    計算の対象となったメインのクラスタについて     |           |
| │　├`"all"`                  |                       総数                        |    int    |
| │　├`"inner"`                |           完全内包されていたクラスタ数            |    int    |
| │　├`"outer"`                |                無関係のクラスタ数                 |    int    |
| │　└`"touch"`                |          重なる領域が存在したクラスタ数           |           |
| │　　├`"have_no_subcluster"` |            内のサブクラスタを持つもの             |    int    |
| │　　└`"have_subclusters"`   |          内のサブクラスタを持たないもの           |    int    |
| │                            |                                                   |           |
| └`"sub_cluster"`             |       計算対象となったサブクラスタについて        |    int    |
| .　　├`"all"`                |                       総数                        |    int    |
| .　　├`"inner"`              |           完全内包されていたクラスタ数            |    int    |
| .　　├`"outer"`              |                無関係のクラスタ数                 |    int    |
| .　　└`"touch"`              |          重なる領域が存在したクラスタ数           |           |
|                              |                                                   |           |
| `"count"`                    |                取得数に関する情報                 |           |
| ├`"limit"`                   |                    取得上限数                     |    int    |
| └`"total"`                   |                   実際の総hit数                   |    int    |
|                              |                                                   |           |
| `"items"`                    |                関連地情報のリスト                 |           |
| └`"LIST[LocationObject]"`    | `"LocationObject"`の内容は[後述](#LocationObject) |           |


### 利用例

```
https://junrei-time-dataapi.herokuapp.com/api/locations_in_circle?lat=35.556243&lon=139.662233&r=10000&limit=10&tag=anime
```

## /locations/budget [GET]

### 概要

中心点(`lat`, `lon`)から, 予算`budget`で行けそうな範囲内にある関連地を取得します.

### パラメータ

|  パラメータ名  | 必須 |                              概要                               | 型名  | デフォルト    | 値域                                      | 備考                          |
|:--------------:|:----:|:---------------------------------------------------------------:|-------|---------------|-------------------------------------------|-------------------------------|
|     `lat`      |  ✓   |                 中心地の緯度(北極=90, 南極=-90)                 | float |               | `-90.0 <= lat <= 90`                      | 0は赤道                       |
|     `lon`      |  ✓   |                   中心地の経度(東→正, 西→負)                    | float |               | `-180.0 <= lon <= 180.0`                  | -180と180は同じ地点           |
|    `budget`    |  ✓   |                           予算(片道)                            | int   |               | `10 <= budget <= 10000`                   |                               |
|  `func_type`   |      |                  距離予測するための関数の種類                   | str   | `d2`          |                                           | 詳細は後述                    |
|     `tag`      |      |    選択対象を`anime`か`drama`, もしくはその両方を選択できる     | str   | `anime,drama` | `"anime", "drama", "anime,drama"`         |                               |
|    `limit`     |      |     取得個数を制限する. 制限時は距離の近いものが取得される.     | int   | `1000`        | `0 < limit`                               |                               |
|   `no_check`   |      | 関連地算出の際, 細かいチェックを行わず, 一部を概算で計算します. | str   | `"false"`     | `"true"`, `"false"`などのそれっぽい文字列 | `&no_check`だと`true`扱い     |
| `no_clustered` |      |           関連地算出の際, クラスタ構造を利用しません.           | str   | `"false"`     | `"true"`, `"false"`などのそれっぽい文字列 | `&no_clustered`だと`true`扱い |

各パラメータにおいて, 値域を満たさない場合, `400 BadRequest` が返却される

### 返却値

#### 全体

```
responce
    ├cluster
    │   ├main_cluster
    │   │   ├all
    │   │   ├inner
    │   │   ├outer
    │   │   └touch
    │   │       ├have_no_subcluster
    │   │       └have_subclusters
    │   │   
    │   └sub_cluster
    │       ├all
    │       ├inner
    │       ├outer
    │       └touch
    │
    ├convert
    │   ├budget
    │   └distance
    │
    ├count
    │   ├limit
    │   └total
    │
    ├items : LIST[LocationObject]
    │
    ├no_check
    │
    ├no_clustered
    │
    ├processing_time
    │
    └tag : List
```

| key                          |                    valueの内容                    | valueの型 |
|:-----------------------------|:-------------------------------------------------:|:---------:|
| `"cluster"`                  |                   クラスタ情報                    |           |
| ├`"main_cluster"`            |    計算の対象となったメインのクラスタについて     |           |
| │　├`"all"`                  |                       総数                        |    int    |
| │　├`"inner"`                |           完全内包されていたクラスタ数            |    int    |
| │　├`"outer"`                |                無関係のクラスタ数                 |    int    |
| │　└`"touch"`                |          重なる領域が存在したクラスタ数           |           |
| │　　├`"have_no_subcluster"` |            内のサブクラスタを持つもの             |    int    |
| │　　└`"have_subclusters"`   |          内のサブクラスタを持たないもの           |    int    |
| │                            |                                                   |           |
| └`"sub_cluster"`             |       計算対象となったサブクラスタについて        |    int    |
| .　　├`"all"`                |                       総数                        |    int    |
| .　　├`"inner"`              |           完全内包されていたクラスタ数            |    int    |
| .　　├`"outer"`              |                無関係のクラスタ数                 |    int    |
| .　　└`"touch"`              |          重なる領域が存在したクラスタ数           |           |
|                              |                                                   |           |
| `"convert"`                  |                金額→距離の変換情報                |           |
| ├`"budget"`                  |                       金額                        |    int    |
| └`"distance"`                |                   変換後の距離                    |   float   |
|                              |                                                   |           |
| `"count"`                    |                取得数に関する情報                 |           |
| ├`"limit"`                   |                    取得上限数                     |    int    |
| └`"total"`                   |                   実際の総hit数                   |    int    |
|                              |                                                   |           |
| `"items"`                    |                関連地情報のリスト                 |           |
| └`"LIST[LocationObject]"`    | `"LocationObject"`の内容は[後述](#LocationObject) |           |
|                              |                                                   |           |
| `"no_check"`                 |              内容は[後述](#no_check)              |           |
|                              |                                                   |           |
| `"no_clustered"`             |            内容は[後述](#no_clustered)            |           |
|                              |                                                   |           |
| `"processing_time"`          |         サーバ上でのクエリ処理時間 [sec]          |   float   |
|                              |                                                   |           |
| `"tag"`                      |                                                   |           |
| └`"LIST[str]"`               |                 対象タグのリスト                  | List[str] |


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

## /locations/title [GET]


### 概要

与えたタイトルに完全一致する作品の関連地情報を取得します.

### パラメータ

| パラメータ名 | 必須 |                          概要                           | 型名 | デフォルト | 値域        | 備考                                                  |
|:------------:|:----:|:-------------------------------------------------------:|------|------------|-------------|-------------------------------------------------------|
|   `title`    |  ✓   |       検索する作品名.ヒットするのは完全一致のみ.        | str  |            |             | 同名でドラマ/アニメの両方が存在する場合もあるので注意 |
|   `limit`    |      | 取得個数を制限する. 制限時は距離の近いものが取得される. | int  | `1000`     | `0 < limit` |                                                       |

各パラメータにおいて, 値域を満たさない場合, `400 BadRequest` が返却される


### 返却値

#### 全体

```
responce
    ├count
    │   ├limit
    │   └total
    │
    ├items : LIST[LocationObject]
    │
    └processing_time
```

| key                       |                    valueの内容                    | valueの型 |
|:--------------------------|:-------------------------------------------------:|:---------:|
| `"count"`                 |                取得数に関する情報                 |           |
| ├`"limit"`                |                    取得上限数                     |    int    |
| └`"total"`                |                   実際の総hit数                   |    int    |
|                           |                                                   |           |
| `"items"`                 |                関連地情報のリスト                 |           |
| └`"LIST[LocationObject]"` | `"LocationObject"`の内容は[後述](#LocationObject) |           |
|                           |                                                   |           |
| `"processing_time"`       |         サーバ上でのクエリ処理時間 [sec]          |   float   |


### 利用例

```
https://junrei-time-dataapi.herokuapp.com/api/locations/title?title=魔王
https://junrei-time-dataapi.herokuapp.com/api/locations/title?title=魔王&limit=10
https://junrei-time-dataapi.herokuapp.com/api/locations/title?title=魔王&limit=999999
```



## データオブジェクトについて

### LocationObject

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

### no_check

仕様とか考えずに適当に載せたので, あったりなかったり扱いづらいです.
一応構造や内容について書いておきます.

#### 概要

パラメータ`no_check`に関する情報が含まれています.


#### 構造と説明

```
responce
    └no_check
        ├enable
        └(missed_check)
```


| key                 |       valueの内容       | valueの型 |
|:--------------------|:-----------------------:|:---------:|
| `"no_check"`        | 内容は[後述](#no_check) |           |
| ├`"enable"`         |                         |           |
| └(`"missed_check"`) |                         |           |

### no_clustered

仕様とか考えずに適当に載せたので, あったりなかったり扱いづらいです.
一応構造や内容について書いておきます.

#### 概要

パラメータ`no_clustered`を有効にしたかどうかを含みます.

#### 構造と説明

```
responce
    └no_clustered
        └enable
```

| key              |         valueの内容         | valueの型 |
|:-----------------|:---------------------------:|:---------:|
| `"no_clustered"` | 内容は[後述](#no_clustered) |           |
| └`"enable"`      |                             |           |


# 作品タイトル関係

## /title/all [GET]


### 概要

データ中に含まれるすべての作品名を取得します.

### パラメータ

| パラメータ名 | 必須 |                       概要                       | 型名 | デフォルト | 値域                                      | 備考                  |
|:------------:|:----:|:------------------------------------------------:|------|------------|-------------------------------------------|-----------------------|
|    `sort`    |      | 返却値を文字列でソート(数字→ローマ字→日本語の順) | str  | `"false"`  | `"true"`, `"false"`などのそれっぽい文字列 | `&sort`だと`true`扱い |

各パラメータにおいて, 値域を満たさない場合, `400 BadRequest` が返却される


### 返却値

#### 全体

```
responce
    ├count
    │   └total
    │
    ├items : LIST[TitleObject]
    │
    ├processing_time
    │
    └sort
```

| key                    |                 valueの内容                 | valueの型 |
|:-----------------------|:-------------------------------------------:|:---------:|
| `"count"`              |             取得数に関する情報              |           |
| └`"total"`             |                実際の総hit数                |    int    |
|                        |                                             |           |
| `"items"`              |             作品名情報のリスト              |           |
| └`"LIST[TitleObject]"` | `"TitleObject"`の内容は[後述](#TitleObject) |           |
|                        |                                             |           |
| `"processing_time"`    |      サーバ上でのクエリ処理時間 [sec]       |   float   |
|                        |                                             |           |
| `"sort"`               | ソートしたかどうか. ソートした場合は`true`  |   bool    |


### 利用例

```
https://junrei-time-dataapi.herokuapp.com/api/title/all
https://junrei-time-dataapi.herokuapp.com/api/title/all&sort
```


## /title/search/startswith [GET]

### 概要

全作品名に対し, 検索ワード(`kw`)が前方一致するものを検索し, そのリストを返します.

### パラメータ

| パラメータ名 | 必須 |                       概要                       | 型名 | デフォルト | 値域                                      | 備考                  |
|:------------:|:----:|:------------------------------------------------:|------|------------|-------------------------------------------|-----------------------|
|     `kw`     |  ✓   |                    検索ワード                    | str  |            |                                           |                       |
|    `kana`    |      |  漢字やカタカナを全て平仮名に変換し, 検索を行う  | str  | `"false"`  | `"true"`, `"false"`などのそれっぽい文字列 | `&kana`だと`true`扱い |
|    `sort`    |      | 返却値を文字列でソート(数字→ローマ字→日本語の順) | str  | `"false"`  | `"true"`, `"false"`などのそれっぽい文字列 | `&sort`だと`true`扱い |

各パラメータにおいて, 値域を満たさない場合, `400 BadRequest` が返却される


### 返却値

```
responce
    ├count
    │   └total
    │
    ├items : LIST[TitleObject]
    │
    ├kana
    │
    ├processing_time
    │
    └sort
```

| key                    |                 valueの内容                 | valueの型 |
|:-----------------------|:-------------------------------------------:|:---------:|
| `"count"`              |             取得数に関する情報              |           |
| └`"total"`             |                実際の総hit数                |    int    |
|                        |                                             |           |
| `"items"`              |             作品名情報のリスト              |           |
| └`"LIST[TitleObject]"` | `"TitleObject"`の内容は[後述](#TitleObject) |           |
|                        |                                             |           |
| `"kana"`               |     かな変換による検索を行ったかどうか      |   bool    |
|                        |                                             |           |
| `"processing_time"`    |      サーバ上でのクエリ処理時間 [sec]       |   float   |
|                        |                                             |           |
| `"sort"`               |             ソートしたかどうか              |   bool    |


### 利用例

```
http://127.0.0.1:8080/api/title/search/startswith?kw=私
http://127.0.0.1:8080/api/title/search/startswith?kw=私&sort
http://127.0.0.1:8080/api/title/search/startswith?kw=私&sort&kana
```


## /title/search/contains [GET]

### 概要

全作品名に対し, 検索ワード(`kw`)が部分一致するものを検索し, そのリストを返します.


### パラメータ

| パラメータ名 | 必須 |                       概要                       | 型名 | デフォルト | 値域                                      | 備考                  |
|:------------:|:----:|:------------------------------------------------:|------|------------|-------------------------------------------|-----------------------|
|     `kw`     |  ✓   |                    検索ワード                    | str  |            |                                           |                       |
|    `kana`    |      |  漢字やカタカナを全て平仮名に変換し, 検索を行う  | str  | `"false"`  | `"true"`, `"false"`などのそれっぽい文字列 | `&kana`だと`true`扱い |
|    `sort`    |      | 返却値を文字列でソート(数字→ローマ字→日本語の順) | str  | `"false"`  | `"true"`, `"false"`などのそれっぽい文字列 | `&sort`だと`true`扱い |

各パラメータにおいて, 値域を満たさない場合, `400 BadRequest` が返却される


### 返却値

```
responce
    ├count
    │   └total
    │
    ├items : LIST[TitleObject]
    │
    ├kana
    │
    ├processing_time
    │
    └sort
```

| key                    |                 valueの内容                 | valueの型 |
|:-----------------------|:-------------------------------------------:|:---------:|
| `"count"`              |             取得数に関する情報              |           |
| └`"total"`             |                実際の総hit数                |    int    |
|                        |                                             |           |
| `"items"`              |             作品名情報のリスト              |           |
| └`"LIST[TitleObject]"` | `"TitleObject"`の内容は[後述](#TitleObject) |           |
|                        |                                             |           |
| `"kana"`               |     かな変換による検索を行ったかどうか      |   bool    |
|                        |                                             |           |
| `"processing_time"`    |      サーバ上でのクエリ処理時間 [sec]       |   float   |
|                        |                                             |           |
| `"sort"`               |             ソートしたかどうか              |   bool    |


### 利用例

```
http://127.0.0.1:8080/api/title/search/contains?kw=私
http://127.0.0.1:8080/api/title/search/contains?kw=私&sort
http://127.0.0.1:8080/api/title/search/contains?kw=私&sort&kana
```

## データオブジェクトについて

### TitleObject

```
TitleObject
    ├title
    └tag
```

|    key    |        valueの内容         | valueの型 |
|:---------:|:--------------------------:|:---------:|
| `"title"` |           作品名           |    str    |
|  `"tag"`  | アニメかドラマかの判別タグ |    str    |


# 関連地数の予測

## /predict/locations_num [GET]

### 概要

中心点(`lat`, `lon`)から半径`r`内の円にある関連地の数を予測します.

### パラメータ


| パラメータ名 | 必須 |              概要               | 型名  | デフォルト | 値域                     | 備考                |
|:------------:|:----:|:-------------------------------:|-------|------------|--------------------------|---------------------|
|    `lat`     |  ✓   | 中心地の緯度(北極=90, 南極=-90) | float |            | `-90.0 <= lat <= 90`     | 0は赤道             |
|    `lon`     |  ✓   |   中心地の経度(東→正, 西→負)    | float |            | `-180.0 <= lon <= 180.0` | -180と180は同じ地点 |
|     `r`      |  ✓   | 中心地からの対象半径(単位は`m`) | int   |            | `0 <= r <= 500000`       |                     |

各パラメータにおいて, 値域を満たさない場合, `400 BadRequest` が返却される

### 返却値

```
responce
    ├predict
    │
    └processing_time
```

| key                 |                 valueの内容                  | valueの型 |
|:--------------------|:--------------------------------------------:|:---------:|
| `"predict"`         | 関連地数の予測値です. 予測値なのでfloatです. |   float   |
|                     |                                              |           |
| `"processing_time"` |       サーバ上でのクエリ処理時間 [sec]       |   float   |


> /predict/locations_num?lat=32.87728801566952&lon=130.598757025641&r=10000