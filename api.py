from flask import Blueprint, request, abort, jsonify
import pandas as pd
import numpy as np

# Blueprint作成 http://host/api 以下のものはここで処理
api = Blueprint('api', __name__, url_prefix='/api')

# /api/locations, [GET]
@api.route('/locations', methods=['GET'])
def get_locations_in_circle():
    """
    hoge

    param
    ----------------------


    return
    ----------------------

    """
    # クエリパラメータの取得
    q_lat = request.args.get('lat', type=float)
    q_lon = request.args.get('lon', type=float)
    q_r = request.args.get('r', type=int)
    q_tag = request.args.get('tag', default="anime,drama", type=str)

    # tag関連のパラメータ
    trim_str_list = ["'", '"', "(", ")", "[", "]"]
    support_tag_list = ["anime", "drama"]

    # latに対するチェック
    if not (-90.0 <= q_lat <= 90.0):
        return "lat", 400

    # lonに対するチェック
    if not (-180.0 <= q_lon <= 180.0):
        return "lon", 400

    # rに対するチェック
    if q_r < 100:
        return "r", 400

    # tagに対する処理とチェック
    for trim_str in trim_str_list:
        q_tag = q_tag.replace(trim_str, "")
    tag_token_list = [token.strip() for token in q_tag.split(",")]
    target_tag_list = [target_tag
                       for target_tag in support_tag_list
                       if target_tag in tag_token_list]
    if len(target_tag_list) <= 0:
        print(tag_token_list)
        return "tag", 400

    # 全体の処理

    info_list = [
        {
            "code": "13106013002",
            "name": "東京都台東区蔵前2丁目",
            "lat": 35.703591,
            "lon": 139.792741,
            "title": "R.O.D",
            "orignal_name": "東京都台東区蔵前2丁目春日通り",
            "scene_in_the_work": "ねねねのマンション近くの橋/全話共通/厩橋",
            "tag": "anime",
        },
        {
            "code": "13106013001",
            "name": "東京都台東区蔵前1丁目",
            "lat": 35.700592,
            "lon": 139.789514,
            "title": "R.O.D",
            "orignal_name": "東京都台東区蔵前1丁目蔵前橋通り",
            "scene_in_the_work": "マンションから追い出された三姉妹が渡った橋/2話/蔵前橋",
            "tag": "anime",
        },
    ]

    # pd.read_csv("./data/anime01.csv")

    return jsonify(info_list), 200

# /api/locations, [GET]
@api.route('/random-locations', methods=['GET'])
def get_random_locations():
    """
    hoge

    param
    ----------------------


    return
    ----------------------

    """
    # クエリパラメータの取得
    q_num = request.args.get('num', default=10, type=int)

    # クエリパラメータに対するチェック
    if q_num > 1000:
        return "要求数が多すぎます", 400
    if q_num < 1:
        return "要求数は0以上の整数である必要がります", 400

    # 全データのロード
    info_list = [{}] * q_num
    df = pd.read_pickle("./data/drama01_df.pkl")
    df = df.append(pd.read_pickle("./data/anime01_df.pkl")).reset_index()

    info_list = [
        {
            "code": series.loc["code"],
            "name": series.loc["name"],
            "lat": float(series.loc["lat"]),
            "lon": float(series.loc["lat"]),
            "title": series.loc["title"],
            "orignal_name": series.loc["orignal_name"],
            "scene_in_the_work": series.loc["scene_in_the_work"],
            "tag": series.loc["tag"],
        }
        for index, series in df.sample(n=q_num).iterrows()
    ]

    return jsonify(info_list), 200


# エラーのハンドリング
@api.errorhandler(400)
@api.errorhandler(404)
def error_handler(error):
    # error.code: HTTPステータスコード
    # error.description: abortで設定したdict型
    return jsonify({'error': {
        'code': error.description['code'],
        'message': error.description['message']
    }}), error.code
