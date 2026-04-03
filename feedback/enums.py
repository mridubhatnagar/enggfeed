from enum import Enum


class FeedbackType(str, Enum):
    TAG = "tag"
    PREREQUISITE = "prerequisite"
    SUMMARY = "summary"
    SIMPLIFY = "simplify"
