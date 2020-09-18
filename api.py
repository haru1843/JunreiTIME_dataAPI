from flask import Blueprint, request, abort, jsonify
import pandas as pd
import numpy as np
import os
import pyproj

# Blueprint作成 http://host/api 以下のものはここで処理
api = Blueprint('api', __name__, url_prefix='/api')


def d1_fitting(d):
    return 57.04183701 * x + -6583.68566879


def d2_fitting(d):
    return -1.42530169e-3 * (x**2) + 6.68895706e1 * x + -1.46801237e4


def d3_fitting(d):
    return -3.07406205e-7*(x**3) + 4.01853773e-3*(x**2) + 4.50963296e1*(x) - 8.39336896e2


def check_circles_state(grs80, lat_c, lon_c, r_c, lat_query, lon_query, r_query):
    _, _, dist = grs80.inv(
        lon_c, lat_c,
        lon_query, lat_query
    )

    if dist <= r_query - r_c:
        return "inner"
    elif dist < r_query + r_c:
        return "touch"
    else:
        return "outer"


def convert_tag_str_to_target_tag_list(tag_str):
    # tag関連のパラメータ
    trim_str_list = ["'", '"', "(", ")", "[", "]"]
    support_tag_list = ["anime", "drama"]

    for trim_str in trim_str_list:
        tag_str = tag_str.replace(trim_str, "")
    tag_token_list = [token.strip() for token in q_tag.split(",")]
    return [target_tag for target_tag in support_tag_list if target_tag in tag_token_list]


# /api/locations_in_circle, [GET]
@api.route('/locations_in_circle', methods=['GET'])
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
    q_limit = request.args.get('limit', default=1000, type=int)

    # latに対するチェック
    if q_lat is None:
        return "parameter 'lat' is required", 400
    elif not (-90.0 <= q_lat <= 90.0):
        return "parameter 'lat' is wrong", 400

    # lonに対するチェック
    if q_lon is None:
        return "parameter 'lon' is required", 400
    elif not (-180.0 <= q_lon <= 180.0):
        return "parameter 'lon' is wrong", 400

    # rに対するチェック
    if q_r is None:
        return "parameter 'r' is required", 400
    elif q_r < 100:
        return "parameter 'r' is too small", 400
    elif q_r > 100000:
        return "parameter 'r' is too large", 400

    # tagに対する処理とチェック
    tag_token_list = convert_tag_str_to_target_tag_list(q_tag)
    target_tag_list = [target_tag
                       for target_tag in support_tag_list
                       if target_tag in tag_token_list]
    if len(target_tag_list) <= 0:
        # print(tag_token_list)
        return "parameter 'tag' is wrong", 400

    if q_limit <= 0:
        return "parameter 'r' must be greater then 0", 400

    # 全体の処理
    clustered_data_dir = "./data/clustered_data/"
    main_cluster_info = pd.read_pickle(os.path.join(clustered_data_dir, "cluster_info.pkl"))

    digit = 3

    target_main_cluster_list = []

    inner_cluster = []  # 完全に内側にあるもの. 判別する必要なし
    touch_cluster = []  # サブクラスタを持ち, 触れているもの. サブクラスタの判定を行う

    check_cluster = []  # サブクラスタを持っていない, 触れているもの. 各点においてチェックが必要

    grs80 = pyproj.Geod(ellps="GRS80")

    # メインクラスタに対するイテレータ処理
    format_str = "{:0" + str(digit) + "}/"
    for idx in range(len(main_cluster_info)):
        nth_cluster_info = main_cluster_info.iloc[idx]
        nth_cluster = nth_cluster_info["nth_cluster"]

        # 距離の比較
        circles_state = check_circles_state(
            grs80,
            nth_cluster_info["lat"],
            nth_cluster_info["lon"],
            nth_cluster_info["max"],
            q_lat, q_lon, q_r
        )

        if circles_state == "outer":
            continue
        elif circles_state == "inner":
            dir_name = format_str.format(nth_cluster)
            inner_cluster.append(os.path.join(clustered_data_dir, dir_name))
        elif circles_state == "touch":
            if not nth_cluster_info["subcluster"]:
                # サブクラスタを持っていない場合
                dir_name = format_str.format(nth_cluster)
                check_cluster.append(os.path.join(clustered_data_dir, dir_name))
            else:
                # サブクラスタを持っている場合
                dir_name = format_str.format(nth_cluster)
                touch_cluster.append(os.path.join(clustered_data_dir, dir_name))
        else:
            return "circles state invalid", 500

    # サブクラスタに対するイテレータ処理
    for sub_cluster_dir in touch_cluster:
        sub_cluster_info = pd.read_pickle(os.path.join(sub_cluster_dir, "cluster_info.pkl"))

        # 距離の比較
        circles_state = check_circles_state(
            grs80,
            sub_cluster_info["lat"],
            sub_cluster_info["lon"],
            sub_cluster_info["max"],
            q_lat, q_lon, q_r
        )

        if circles_state == "outer":
            continue
        elif circles_state == "inner":
            dir_name = format_str.format(nth_cluster)
            inner_cluster.append(os.path.join(clustered_data_dir, dir_name))
        elif circles_state == "touch":
            if not nth_cluster_info["subcluster"]:
                # サブクラスタを持っていない場合
                dir_name = format_str.format(nth_cluster)
                check_cluster.append(os.path.join(clustered_data_dir, dir_name))
            else:
                # サブクラスタを持っている場合
                dir_name = format_str.format(nth_cluster)
                touch_cluster.append(os.path.join(clustered_data_dir, dir_name))
        else:
            return "circles state invalid", 500

    info_list = []

    # 内包円でなく, 重なっているクラスタに対して, 各要素で範囲内にあるかをチェック
    for check_cluster_dir in check_cluster:
        all_df = pd.read_pickle(os.path.join(check_cluster_dir, "all.pkl"))

        # クラスターの情報の計算
        target_num = len(all_df)
        center_point_lat = [q_lat] * target_num
        center_point_lon = [q_lon] * target_num

        _, _, dist = grs80.inv(
            center_point_lon, center_point_lat,
            all_df["lon"].to_numpy(),
            all_df["lat"].to_numpy()
        )

        # @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
        # @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
        all_df["distance"] = dist
        # @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
        # @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

        if sum(dist <= q_r) > 0:
            info_list += all_df[dist <= q_r].to_dict(orient="records")

    # クラスタが完全に内包されている場合, その要素は全て追加
    for inner_cluster_dir in inner_cluster:
        all_df = pd.read_pickle(os.path.join(inner_cluster_dir, "all.pkl"))

        # @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
        # @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
        # クラスターの情報の計算
        target_num = len(all_df)
        center_point_lat = [q_lat] * target_num
        center_point_lon = [q_lon] * target_num

        _, _, dist = grs80.inv(
            center_point_lon, center_point_lat,
            all_df["lon"].to_numpy(),
            all_df["lat"].to_numpy()
        )
        all_df["distance"] = dist
        # @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
        # @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

        if len(all_df) > 0:
            info_list += all_df.to_dict(orient="records")

    info_list = list(filter(lambda x: x["tag"] in target_tag_list, info_list))

    total = len(info_list)

    info_list.sort(key=lambda x: x["distance"])

    if total > q_limit:
        info_list = info_list[:q_limit]

    count_dict = {
        "total": total,
        "limit": q_limit
    }

    return jsonify({"count": count_dict, "items": info_list}), 200

# /api/locations, [GET]
@api.route('/random_locations', methods=['GET'])
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
            "lon": float(series.loc["lon"]),
            "title": series.loc["title"],
            "orignal_name": series.loc["orignal_name"],
            "scene_in_the_work": series.loc["scene_in_the_work"],
            "tag": series.loc["tag"],
        }
        for index, series in df.sample(n=q_num).iterrows()
    ]

    return jsonify({"count": {"total": q_num}, "items": info_list}), 200


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
