from flask import Blueprint, request, abort, jsonify
import pandas as pd
import numpy as np
import os
import pyproj
from distutils.util import strtobool as s2b
import time
from pykakasi import kakasi


# Blueprint作成 http://host/api 以下のものはここで処理
api = Blueprint('api', __name__, url_prefix='/api')


class StringFormatter:
    def __init__(self):
        trim_char = [" ", "　", "(", ")", "～", "→", ";", ":", "☆", ".", "－", "-",
                     "【", "】", "『", "』", "∞", "/", "／", "♪", "（", "）", "<", ">", "★", "▷", "△",
                     "ー", "＜", "＞", "！", "？", "・", "!", "?", "×", "、", "。"]
        before = [chr(0xff01 + i) for i in range(94)] + trim_char

        after = [chr(0x21 + i) for i in range(94)] + ([""] * len(trim_char))

        self.map_table = str.maketrans(dict([(x, y) for x, y in zip(before, after)]))
        self.kks = kakasi()

    def sanitize(self, string):
        return string.translate(self.map_table).lower()

    def convert_str_to_kana(self, string):
        return "".join([token["hira"] for token in self.kks.convert(string)])


def d1_fitting(budget):
    # return 57.04183701 * budget + -6583.68566879
    return (74.32884302 * budget) - 17376.6623352


def d2_fitting(budget):
    # return -1.42530169e-3 * (budget**2) + 6.68895706e1 * budget + -1.46801237e4
    return 7.25810716e-03 * (budget**2) + (4.88282995e+01 * budget) - 4.94836817e+03


def d3_fitting(budget):
    # return -3.07406205e-7*(budget**3) + 4.01853773e-3*(budget**2) + 4.50963296e1*(budget) - 8.39336896e2
    return -9.05759095e-06 * (budget**3) + 5.57103185e-02 * (budget**2) - 9.18636189*(budget) + 1.13578072e+04


def predict_locations_num(lat, lon, r, grs80):
    p1 = {"lat": 35.655094385177414, "lon": 139.63625767563855}  # 世田谷
    _, _, d1 = grs80.inv(
        p1["lon"], p1["lat"],
        lon, lat
    )

    scaled_r = r / 1e6
    diff = d1 - r
    sigmoid_diff = np.where(
        diff < 10000,
        1 / (1 + np.exp((5000 - diff)/-10000)),
        0
    )

    return 1e4 * (
        + (1.05728914*scaled_r)
        + (2.07445777*(scaled_r**2))
        + (1.73280175*sigmoid_diff)
        + (5.10539971*(sigmoid_diff**2))
        - 0.00390048
    )


def check_some_circles_state(grs80, lat_c, lon_c, r_c, lat_query, lon_query, r_query):

    try:
        _, _, dist = grs80.inv(
            lon_c, lat_c,
            lon_query, lat_query
        )
    except TypeError:
        string = f"{type(lon_c)}, {type(lat_c)}"
        string += f"{type(lon_query)}, {type(lat_query)}"
        raise TypeError(string)

    dist = np.array(dist)

    # numpyの文字列型 '<U5' を利用
    circles_state = np.empty(len(dist), dtype="<U5")

    circles_state[dist <= r_query - r_c] = "inner"
    circles_state[(dist < r_query + r_c) & (circles_state == "")] = "touch"
    circles_state[circles_state == ""] = "outer"
    return circles_state


def convert_boolean_str_to_bool(boolean_str: str):
    try:
        return s2b(boolean_str) != 0
    except ValueError:
        return None


def convert_tag_str_to_target_tag_list(tag_str: str):
    # tag関連のパラメータ
    trim_str_list = ["'", '"', "(", ")", "[", "]"]
    support_tag_list = ["anime", "drama"]

    for trim_str in trim_str_list:
        tag_str = tag_str.replace(trim_str, "")
    tag_token_list = [token.strip() for token in tag_str.split(",")]
    return [target_tag for target_tag in support_tag_list if target_tag in tag_token_list]


def is_lat_wrong(lat: float):
    if lat is None:
        return {"msg": "parameter 'lat' is required", "status_code": 400}
    elif not (-90.0 <= lat <= 90.0):
        return {"msg": "parameter 'lat' is wrong", "status_code": 400}

    return False


def is_lon_wrong(lon: float):
    if lon is None:
        return {"msg": "parameter 'lon' is required", "status_code": 400}
    elif not (-180.0 <= lon <= 180.0):
        return {"msg": "parameter 'lon' is wrong", "status_code": 400}

    return False


def is_r_wrong(r: int):
    if r is None:
        return {"msg": "parameter 'r' is required", "status_code": 400}
    elif r < 0:
        return {"msg": "parameter 'r' is too small", "status_code": 400}
    elif r > 500000:
        return {"msg": "parameter 'r' is too large", "status_code": 400}

    return False


def is_budget_wrong(budget: int):
    if budget is None:
        return {"msg": "parameter 'budget' is required", "status_code": 400}
    elif budget < 10:
        return {"msg": "parameter 'budget' is too small", "status_code": 400}
    elif budget > 10000:
        return {"msg": "parameter 'budget' is too large", "status_code": 400}

    return False


def get_fitting_func_from_func_type(func_type: str):
    support_func_type_mapping = {
        "d1": d1_fitting, "d2": d2_fitting, "d3": d3_fitting
    }

    if func_type not in support_func_type_mapping.keys():
        return None

    return support_func_type_mapping[func_type]


def calc_locations_in_circle_for_no_clustered(q_lat, q_lon, q_r, q_tag, q_limit, target_tag_list, no_check=False):
    clustered_data_dir = "./data/clustered_data/"

    info_list = []

    grs80 = pyproj.Geod(ellps="GRS80")

    check_cluster_df = pd.read_pickle(
        os.path.join(clustered_data_dir, "all.pkl")
    )

    target_num = len(check_cluster_df)
    center_point_lat = [q_lat] * target_num
    center_point_lon = [q_lon] * target_num
    _, _, dist = grs80.inv(
        center_point_lon, center_point_lat,
        check_cluster_df["lon"].to_numpy(),
        check_cluster_df["lat"].to_numpy()
    )
    check_cluster_df["distance"] = dist
    if np.any(dist <= q_r):
        info_list += check_cluster_df[dist <= q_r].to_dict(orient="records")

    # 対象タグのみ取り出す
    info_list = list(filter(lambda x: x["tag"] in target_tag_list, info_list))

    # 制限前の総数を保存
    total = len(info_list)

    # クエリで与えられた緯度経度から近い要素順(距離昇順)でソート
    info_list.sort(key=lambda x: x["distance"])

    # responsの量を制限
    if total > q_limit:
        info_list = info_list[:q_limit]

    # responseに加えるcount情報
    count_dict = {
        "total": total,
        "limit": q_limit
    }

    return {
        "count": count_dict,
        "items": info_list
    }, 200


def calc_locations_in_circle(q_lat, q_lon, q_r, q_tag, q_limit, target_tag_list, no_check=False):
    clustered_data_dir = "./data/clustered_data/"

    digit = 3
    fmt_str = "{:0" + str(digit) + "}/"

    target_main_cluster_list = []

    cluster_info = {}
    no_check_info = {}
    info_list = []

    main_cluster_info = pd.read_pickle(os.path.join(clustered_data_dir, "cluster_info.pkl"))
    grs80 = pyproj.Geod(ellps="GRS80")

    # メインクラスタに対する, クラスタ内包状態の確認
    main_cluster_num = len(main_cluster_info)
    circles_state = check_some_circles_state(
        grs80,
        main_cluster_info["lat"].to_numpy(),
        main_cluster_info["lon"].to_numpy(),
        main_cluster_info["max"].to_numpy(),
        [q_lat]*main_cluster_num, [q_lon]*main_cluster_num, [q_r]*main_cluster_num
    )

    inner_nth_main_cluster_list = \
        main_cluster_info[circles_state == "inner"]["nth_cluster"].to_list()

    no_check_info["enable"] = no_check
    if no_check:
        tmp_len = len(inner_nth_main_cluster_list)

        inner_nth_main_cluster_list += \
            main_cluster_info[circles_state == "touch"]["nth_cluster"].to_list()
        touch_nth_main_cluster_list = []
        check_nth_main_cluster_list = []

        no_check_info["missed_check"] = len(inner_nth_main_cluster_list) - tmp_len
    else:
        have_subcluster = (circles_state == "touch") & main_cluster_info["subcluster"]
        no_subcluster = (circles_state == "touch") & (~main_cluster_info["subcluster"])
        touch_nth_main_cluster_list = main_cluster_info[have_subcluster]["nth_cluster"].to_list()
        check_nth_main_cluster_list = main_cluster_info[no_subcluster]["nth_cluster"].to_list()

    cluster_info["main_cluster"] = {
        "all": len(main_cluster_info),
        "inner": len(inner_nth_main_cluster_list),
        "touch": {
            "have_subclusters": len(touch_nth_main_cluster_list),
            "have_no_subcluster": len(check_nth_main_cluster_list),
        },
        "outer": len(main_cluster_info) - (len(inner_nth_main_cluster_list) +
                                           len(check_nth_main_cluster_list) +
                                           len(touch_nth_main_cluster_list))
    }

    # サブクラスタに対する, クラスタ内包状態の確認
    # メインクラスタごとに, サブクラスタの情報を読み込む(親クラスタ番号も付与)
    if len(touch_nth_main_cluster_list) > 0:
        sub_cluster_info = pd.concat([
            pd.read_pickle(
                os.path.join(clustered_data_dir, fmt_str.format(
                    touch_nth_cluster), "cluster_info.pkl")
            ).assign(parent_nth_cluster=touch_nth_cluster)
            for touch_nth_cluster in touch_nth_main_cluster_list
        ]).reset_index(drop=True)

        sub_cluster_num = len(sub_cluster_info)
        circles_state = check_some_circles_state(
            grs80,
            sub_cluster_info["lat"].to_numpy(),
            sub_cluster_info["lon"].to_numpy(),
            sub_cluster_info["max"].to_numpy(),
            [q_lat]*sub_cluster_num, [q_lon]*sub_cluster_num, [q_r]*sub_cluster_num
        )

        inner_nth_sub_cluster_list = \
            sub_cluster_info[circles_state == "inner"][[
                "parent_nth_cluster", "nth_cluster"]].values.tolist()

        check_nth_sub_cluster_list = \
            sub_cluster_info[circles_state == "touch"][[
                "parent_nth_cluster", "nth_cluster"]].values.tolist()

        cluster_info["sub_cluster"] = {
            "all": len(sub_cluster_info),
            "inner": len(inner_nth_sub_cluster_list),
            "touch": len(check_nth_sub_cluster_list),
            "outer": len(sub_cluster_info) - (
                len(inner_nth_sub_cluster_list) + len(check_nth_sub_cluster_list)
            )
        }
    else:
        cluster_info["sub_cluster"] = {"all": 0}

    # touch-clusterに対する処理
    # 内包円でなく, 重なっているクラスタに対して, 各要素で範囲内にあるかをチェック
    check_cluster_dir_path_list = [
        os.path.join(clustered_data_dir, fmt_str.format(check_nth_main_cluster))
        for check_nth_main_cluster in check_nth_main_cluster_list
    ]
    if len(touch_nth_main_cluster_list) > 0:
        check_cluster_dir_path_list += [
            os.path.join(clustered_data_dir,
                         fmt_str.format(parent_cluster),
                         fmt_str.format(check_nth_sub_cluster))
            for parent_cluster, check_nth_sub_cluster in check_nth_sub_cluster_list
        ]

    if len(check_cluster_dir_path_list) > 0:
        check_cluster_df = pd.concat([
            pd.read_pickle(os.path.join(check_cluster_dir_path, "all.pkl"))
            for check_cluster_dir_path in check_cluster_dir_path_list
        ])
        target_num = len(check_cluster_df)
        center_point_lat = [q_lat] * target_num
        center_point_lon = [q_lon] * target_num
        _, _, dist = grs80.inv(
            center_point_lon, center_point_lat,
            check_cluster_df["lon"].to_numpy(),
            check_cluster_df["lat"].to_numpy()
        )
        check_cluster_df["distance"] = dist
        if np.any(dist <= q_r):
            info_list += check_cluster_df[dist <= q_r].to_dict(orient="records")

    # inner-clusterに対する処理
    # クラスタが完全に内包されている場合, その要素は全て追加
    inner_cluster_dir_path_list = [
        os.path.join(clustered_data_dir, fmt_str.format(inner_nth_main_cluster))
        for inner_nth_main_cluster in inner_nth_main_cluster_list
    ]
    if len(touch_nth_main_cluster_list) > 0:
        inner_cluster_dir_path_list += [
            os.path.join(clustered_data_dir,
                         fmt_str.format(parent_cluster),
                         fmt_str.format(inner_nth_sub_cluster))
            for parent_cluster, inner_nth_sub_cluster in inner_nth_sub_cluster_list
        ]

    if len(inner_cluster_dir_path_list) > 0:
        inner_cluster_df = pd.concat([
            pd.read_pickle(os.path.join(inner_cluster_dir_path, "all.pkl"))
            for inner_cluster_dir_path in inner_cluster_dir_path_list
        ])

        # inner-clusterでは距離の比較は必要ないが, レコードに距離情報を付与させるため計算する
        target_num = len(inner_cluster_df)
        center_point_lat = [q_lat] * target_num
        center_point_lon = [q_lon] * target_num
        _, _, dist = grs80.inv(
            center_point_lon, center_point_lat,
            inner_cluster_df["lon"].to_numpy(),
            inner_cluster_df["lat"].to_numpy()
        )
        inner_cluster_df["distance"] = dist
        if len(inner_cluster_df) > 0:
            info_list += inner_cluster_df.to_dict(orient="records")

    # 対象タグのみ取り出す
    info_list = list(filter(lambda x: x["tag"] in target_tag_list, info_list))

    # 制限前の総数を保存
    total = len(info_list)

    # クエリで与えられた緯度経度から近い要素順(距離昇順)でソート
    info_list.sort(key=lambda x: x["distance"])

    # responsの量を制限
    if total > q_limit:
        info_list = info_list[:q_limit]

    # responseに加えるcount情報
    count_dict = {
        "total": total,
        "limit": q_limit
    }

    return {
        "count": count_dict,
        "items": info_list,
        "cluster": cluster_info,
        "no_check": no_check_info
    }, 200


def title_search(kw=None, search_type="startswith", sort=False, kana=False):

    titles_df = pd.read_pickle("./data/titles.pkl")

    if kw is not None:
        str_formatter = StringFormatter()

        kw = str_formatter.sanitize(kw)
        if kana:
            kw = str_formatter.convert_str_to_kana(kw)
            column_name = "sanitized_kana"
        else:
            column_name = "sanitized_title"

        if search_type == "startswith":
            titles_df = titles_df.query(f'{column_name}.str.startswith("{kw}")', engine="python")
            # title_list = [
            #     title for title in title_list
            #     if title.lower().translate(zenkaku2hankaku).startswith(sanitized_kw)
            # ]
        elif search_type == "contains":
            titles_df = titles_df.query(f'{column_name}.str.contains("{kw}")', engine="python")
            # title_list = [
            #     title for title in title_list
            #     if sanitized_kw in title.lower().translate(zenkaku2hankaku)
            # ]
        else:
            raise ValueError("選択したサーチ方法が見つかりません.")

    if sort:
        return titles_df.sort_values("sanitized_kana")
    else:
        return titles_df

# /api/title/all
@api.route('/title/all', methods=['GET'])
def get_all_titles():
    start_time = time.time()

    q_sort = request.args.get('sort', default="false", type=str)

    if q_sort == "":
        converted_sort = True
    else:
        converted_sort = convert_boolean_str_to_bool(q_sort)
        if converted_sort is None:
            return jsonify({
                "msg": f"Non-supporting format in 'sort' : {q_sort}",
                "invalid_param": "sort",
            }), 400

    item_list = title_search(sort=converted_sort)[["title", "tag"]].to_dict(orient="records")

    rtn_dict = {
        "count": {
            "total": len(item_list),
        },
        "items": item_list,
        "processing_time": time.time() - start_time,
        "sort": converted_sort
    }

    return jsonify(rtn_dict), 200


# /api/title/search/startswith
@api.route('/title/search/startswith', methods=['GET'])
def search_titles_startswith():
    start_time = time.time()

    q_kw = request.args.get('kw', default="", type=str)
    q_sort = request.args.get('sort', default="false", type=str)
    q_kana = request.args.get('kana', default="false", type=str)

    if len(q_kw) <= 0:
        return jsonify({
            "msg": "'kw' is not set",
            "invalid_param": "kw",
        }), 400

    if q_sort == "":
        converted_sort = True
    else:
        converted_sort = convert_boolean_str_to_bool(q_sort)
        if converted_sort is None:
            return jsonify({
                "msg": f"Non-supporting format in 'sort' : {q_sort}",
                "invalid_param": "sort",
            }), 400

    if q_kana == "":
        converted_kana = True
    else:
        converted_kana = convert_boolean_str_to_bool(q_kana)
        if converted_kana is None:
            return jsonify({
                "msg": f"Non-supporting format in 'kana' : {q_kana}",
                "invalid_param": "sort",
            }), 400

    item_list = title_search(kw=q_kw, search_type="startswith",
                             sort=converted_sort, kana=converted_kana)[["title", "tag"]].to_dict(orient="records")

    rtn_dict = {
        "count": {
            "total": len(item_list),
        },
        "items": item_list,
        "processing_time": time.time() - start_time,
        "sort": converted_sort,
        "kana": converted_kana,
    }
    return jsonify(rtn_dict), 200


# /api/title/search/contains
@api.route('/title/search/contains', methods=['GET'])
def search_titles_contains():
    start_time = time.time()

    q_kw = request.args.get('kw', default="", type=str)
    q_sort = request.args.get('sort', default="false", type=str)
    q_kana = request.args.get('kana', default="false", type=str)

    if len(q_kw) <= 0:
        return jsonify({
            "msg": "'kw' is not set",
            "invalid_param": "kw",
        }), 400

    if q_sort == "":
        converted_sort = True
    else:
        converted_sort = convert_boolean_str_to_bool(q_sort)
        if converted_sort is None:
            return jsonify({
                "msg": f"Non-supporting format in 'sort' : {q_sort}",
                "invalid_param": "sort",
            }), 400

    if q_kana == "":
        converted_kana = True
    else:
        converted_kana = convert_boolean_str_to_bool(q_kana)
        if converted_kana is None:
            return jsonify({
                "msg": f"Non-supporting format in 'kana' : {q_kana}",
                "invalid_param": "sort",
            }), 400

    item_list = title_search(kw=q_kw, search_type="contains",
                             sort=converted_sort, kana=converted_kana)[["title", "tag"]].to_dict(orient="records")

    rtn_dict = {
        "count": {
            "total": len(item_list),
        },
        "items": item_list,
        "processing_time": time.time() - start_time,
        "sort": converted_sort,
        "kana": converted_kana,
    }
    return jsonify(rtn_dict), 200


# /api/locations/titles
@api.route('/locations/title', methods=['GET'])
def get_locations_by_title():
    start_time = time.time()

    q_title = request.args.get('title', type=str)
    q_limit = request.args.get('limit', default=1000, type=int)

    if q_title is None:
        return jsonify({
            "msg": "parameter 'title' is required",
            "invalid_param": "title",
        }), 400

    # limitに対するチェック
    if q_limit <= 0:
        return jsonify({
            "msg": "parameter 'limit' must be greater then 0",
            "invalid_param": "limit",
        }), 400

    clustered_data_dir = "./data/clustered_data/"
    df = pd.read_pickle(
        os.path.join(clustered_data_dir, "all.pkl")
    ).query("title == @q_title")

    rtn_dict = {
        "count": {
            "total": len(df),
            "limit": q_limit
        },
        "items": df.to_dict(orient="records")[:q_limit],
        "processing_time": time.time() - start_time,
    }

    return jsonify(rtn_dict), 200

# /api/locations_within_budget, [GET]
# /api/locations/within_budget, [GET]
@api.route('/locations_within_budget', methods=['GET'])  # そのうち消す
@api.route('/locations/budget', methods=['GET'])
def get_locations_within_budget():
    start_time = time.time()

    # クエリパラメータの取得
    q_lat = request.args.get('lat', type=float)
    q_lon = request.args.get('lon', type=float)
    q_budget = request.args.get('budget', type=int)
    q_func_type = request.args.get('func_type', default="d2", type=str)
    q_tag = request.args.get('tag', default="anime,drama", type=str)
    q_limit = request.args.get('limit', default=1000, type=int)
    q_no_check = request.args.get('no_check', default="false", type=str)
    q_no_clustered = request.args.get('no_clustered', default="false", type=str)

    # latに対するチェック
    lat_is_wrong = is_lat_wrong(q_lat)
    if lat_is_wrong:
        return jsonify({
            "msg": lat_is_wrong["msg"],
            "invalid_param": "lat",
        }), lat_is_wrong["status_code"]
    # lonに対するチェック
    lon_is_wrong = is_lon_wrong(q_lon)
    if lon_is_wrong:
        return jsonify({
            "msg": lon_is_wrong["msg"],
            "invalid_param": "lon",
        }), lon_is_wrong["status_code"]

    # budgetに対するチェック
    budget_is_wrong = is_budget_wrong(q_budget)
    if budget_is_wrong:
        return jsonify({
            "msg": budget_is_wrong["msg"],
            "invalid_param": "budget",
        }), budget_is_wrong["status_code"]

    # func_typeから対応する変換のための関数を取得
    fitting_func = get_fitting_func_from_func_type(q_func_type)
    if fitting_func is None:
        return jsonify({
            "msg": f"Non-supporting function type : '{q_func_type}'",
            "invalid_param": "func_type",
        }), 400
    calc_r = fitting_func(q_budget)

    # rに対するチェック
    r_is_wrong = is_r_wrong(calc_r)
    if r_is_wrong:
        return jsonify({
            "msg": r_is_wrong["msg"].replace("'r'", "'converted r'"),
            "invalid_param": "budget",
        }), r_is_wrong["status_code"]

    # tagに対する処理とチェック
    target_tag_list = convert_tag_str_to_target_tag_list(q_tag)
    if len(target_tag_list) <= 0:
        return jsonify({
            "msg": f"Non-supporting tag : '{q_tag}'",
            "invalid_param": "tag",
        }), 400

    # limitに対するチェック
    if q_limit <= 0:
        return jsonify({
            "msg": "parameter 'limit' must be greater then 0",
            "invalid_param": "limit",
        }), 400

    # no_checkに対する変換とチェック
    if q_no_check == "":
        converted_no_check = True
    else:
        converted_no_check = convert_boolean_str_to_bool(q_no_check)
        if converted_no_check is None:
            return jsonify({
                "msg": f"Non-supporting format in 'no_check' : {q_no_check}",
                "invalid_param": "no_check",
            }), 400

    # no_clusteredに対する変換とチェック
    if q_no_clustered == "":
        converted_no_clustered = True
    else:
        converted_no_clustered = convert_boolean_str_to_bool(q_no_clustered)
        if converted_no_clustered is None:
            return jsonify({
                "msg": f"Non-supporting format in 'no_clustered' : {q_no_clustered}",
                "invalid_param": "no_clustered",
            }), 400

    # 全体の処理
    if converted_no_clustered:
        rtn_dict, status_code = calc_locations_in_circle_for_no_clustered(
            q_lat=q_lat, q_lon=q_lon, q_r=calc_r,
            q_tag=q_tag, q_limit=q_limit, target_tag_list=target_tag_list,
        )
    else:
        rtn_dict, status_code = calc_locations_in_circle(
            q_lat=q_lat, q_lon=q_lon, q_r=calc_r,
            q_tag=q_tag, q_limit=q_limit, target_tag_list=target_tag_list,
            no_check=converted_no_check
        )
    rtn_dict["convert"] = {"budget": q_budget, "distance": calc_r}
    rtn_dict["no_clustered"] = {"enable": converted_no_clustered}
    rtn_dict["tag"] = target_tag_list
    rtn_dict["processing_time"] = time.time() - start_time
    return jsonify(rtn_dict), status_code

# /api/locations_in_circle, [GET]
# /api/locations_in_circle, [GET]
@api.route('/locations_in_circle', methods=['GET'])   # そのうち消す
@api.route('/locations/circle', methods=['GET'])
def get_locations_in_circle():
    start_time = time.time()

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
    q_no_check = request.args.get('no_check', default="false", type=str)
    q_no_clustered = request.args.get('no_clustered', default="false", type=str)

    # latに対するチェック
    lat_is_wrong = is_lat_wrong(q_lat)
    if lat_is_wrong:
        return jsonify({
            "msg": lat_is_wrong["msg"],
            "invalid_param": "lat",
        }), lat_is_wrong["status_code"]
    # lonに対するチェック
    lon_is_wrong = is_lon_wrong(q_lon)
    if lon_is_wrong:
        return jsonify({
            "msg": lon_is_wrong["msg"],
            "invalid_param": "lon",
        }), lon_is_wrong["status_code"]

    # rに対するチェック
    r_is_wrong = is_r_wrong(q_r)
    if r_is_wrong:
        return jsonify({
            "msg": r_is_wrong["msg"],
            "invalid_param": "r",
        }), r_is_wrong["status_code"]

    # tagに対する処理とチェック
    target_tag_list = convert_tag_str_to_target_tag_list(q_tag)
    if len(target_tag_list) <= 0:
        return jsonify({
            "msg": f"Non-supporting tag : '{q_tag}'",
            "invalid_param": "tag",
        }), 400

    # limitに対するチェック
    if q_limit <= 0:
        return jsonify({
            "msg": "parameter 'limit' must be greater then 0",
            "invalid_param": "limit",
        }), 400

    # no_checkに対する変換とチェック
    if q_no_check == "":
        converted_no_check = True
    else:
        converted_no_check = convert_boolean_str_to_bool(q_no_check)
        if converted_no_check is None:
            return jsonify({
                "msg": f"Non-supporting format in 'no_check' : {q_no_check}",
                "invalid_param": "no_check",
            }), 400

    # no_clusteredに対する変換とチェック
    if q_no_clustered == "":
        converted_no_clustered = True
    else:
        converted_no_clustered = convert_boolean_str_to_bool(q_no_clustered)
        if converted_no_clustered is None:
            return jsonify({
                "msg": f"Non-supporting format in 'no_clustered' : {q_no_clustered}",
                "invalid_param": "no_clustered",
            }), 400

    # 全体の処理
    if converted_no_clustered:
        rtn_dict, status_code = calc_locations_in_circle_for_no_clustered(
            q_lat=q_lat, q_lon=q_lon, q_r=q_r,
            q_tag=q_tag, q_limit=q_limit, target_tag_list=target_tag_list,
        )
    else:
        rtn_dict, status_code = calc_locations_in_circle(
            q_lat=q_lat, q_lon=q_lon, q_r=q_r,
            q_tag=q_tag, q_limit=q_limit, target_tag_list=target_tag_list,
            no_check=converted_no_check
        )

    rtn_dict["no_clustered"] = {"enable": converted_no_clustered}
    rtn_dict["tag"] = target_tag_list
    rtn_dict["processing_time"] = time.time() - start_time
    return jsonify(rtn_dict), status_code

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


# /api/predict/locations_num [GET]
@api.route('/predict/locations_num', methods=['GET'])
def get_locations_num():
    start_time = time.time()

    q_lat = request.args.get('lat', type=float)
    q_lon = request.args.get('lon', type=float)
    q_r = request.args.get('r', type=int)

    # latに対するチェック
    lat_is_wrong = is_lat_wrong(q_lat)
    if lat_is_wrong:
        return jsonify({
            "msg": lat_is_wrong["msg"],
            "invalid_param": "lat",
        }), lat_is_wrong["status_code"]

    # lonに対するチェック
    lon_is_wrong = is_lon_wrong(q_lon)
    if lon_is_wrong:
        return jsonify({
            "msg": lon_is_wrong["msg"],
            "invalid_param": "lon",
        }), lon_is_wrong["status_code"]

    # rに対するチェック
    r_is_wrong = is_r_wrong(q_r)
    if r_is_wrong:
        return jsonify({
            "msg": r_is_wrong["msg"],
            "invalid_param": "r",
        }), r_is_wrong["status_code"]

    grs80 = pyproj.Geod(ellps="GRS80")
    predicted_num = predict_locations_num(q_lat, q_lon, q_r, grs80)

    rtn_dict = {
        "predict": predicted_num,
        "processing_time": time.time() - start_time,
    }

    return jsonify(rtn_dict), 200


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
