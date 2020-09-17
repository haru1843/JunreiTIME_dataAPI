# APIの概要

ドラマやアニメにゆかりのある土地の情報を取得するためのAPIです.


# APIの仕様

ホスト : `https://junrei-time-dataapi.herokuapp.com/api/`

## /random_locations [GET] (実装済み)

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

## /locations_in_circle [GET] (実装済み)

### 概要

中心点(lat, lon)から半径r内の円にある関連地を取得します.

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