# -*- coding: utf-8 -*-
"""V5.1 character-theme prompt components, with separate SFW/NSFW pools."""

from __future__ import annotations

import random

COMPONENTS = {
    "SFW": {
        "服装": [
            "黑色长风衣", "白色衬衫和深色长裤", "复古西装", "白色针织衫和长裙",
            "轻便运动装", "夏日连衣裙", "中式立领上衣", "深色高领毛衣",
            "牛仔外套和休闲裤", "舞台礼服",
        ],
        "场景": [
            "雨后的城市街道", "安静的旧图书馆", "海边黄昏", "森林晨雾",
            "山间木屋", "城市天台夜景", "老式咖啡馆", "雪后的公园",
            "空旷剧场", "复古火车站",
        ],
        "表情": [
            "安静地看向镜头", "温柔的微笑", "侧脸沉思", "自信地直视前方",
            "轻松自然的笑意", "略带惊讶的神情",
        ],
        "光线": [
            "柔和的窗边自然光", "电影感侧逆光", "黄昏暖色轮廓光", "冷色月光",
            "低调的室内灯光", "清晨薄雾中的散射光",
        ],
        "镜头": [
            "85mm 人像特写", "50mm 自然视角", "中景半身构图", "低角度英雄视角",
            "广角环境人像", "浅景深近景",
        ],
        "氛围": [
            "安静而克制", "温暖治愈", "怀旧电影感", "清爽明亮",
            "孤独而诗意", "轻松的生活感",
        ],
    },
    "NSFW": {
        "服装": [
            "黑色蕾丝内衣", "丝绸吊带睡裙", "白色浴袍", "黑色长手套和晚礼服",
            "泳装和薄纱外搭", "黑色吊带袜", "敞开的白衬衫", "束腰和丝绸长裙",
            "针织开衫滑落肩头", "蕾丝睡袍",
        ],
        "场景": [
            "酒店套房", "私密卧室", "浴室雾气", "海边私人泳池",
            "夜晚阳台", "复古公寓", "山间温泉", "私密更衣室",
            "落地窗前的沙发", "烛光浴室",
        ],
        "表情": [
            "慵懒地看向镜头", "意味深长的微笑", "半闭着眼睛", "侧脸低垂视线",
            "放松而自信", "安静的邀请感",
        ],
        "光线": [
            "暖色台灯", "低调轮廓光", "浴室雾气中的柔光", "夜间城市霓虹",
            "烛光", "清晨床边的侧光",
        ],
        "镜头": [
            "私房半身构图", "浅景深近景", "低角度人像", "镜前构图",
            "中景环境人像", "亲密视角特写",
        ],
        "氛围": [
            "私密而安静", "成熟慵懒", "暧昧的电影感", "克制的性感",
            "夜晚的松弛感", "温柔而危险",
        ],
    },
}

DEFAULT_KEYS = ("服装", "场景")


def keys(sfw=True):
    return list(COMPONENTS["SFW" if sfw else "NSFW"].keys())


def pick(sfw=True, selected=None, rng=None):
    rng = rng or random
    pool = COMPONENTS["SFW" if sfw else "NSFW"]
    selected = list(selected or DEFAULT_KEYS)
    out = {}
    for key in selected:
        vals = pool.get(key) or []
        if vals:
            out[key] = rng.choice(vals)
    return out


def compose(components):
    """Return a neat Chinese suffix; components are already phrase-sized."""
    parts = []
    for key in ("服装", "场景", "表情", "光线", "镜头", "氛围"):
        value = components.get(key)
        if value:
            parts.append(f"{key}：{value}")
    return "，".join(parts)
