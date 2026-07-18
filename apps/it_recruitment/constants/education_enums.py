from django.db import models


class EducationLevel(models.TextChoices):
    SCHOOL = "school", "School (SSC / 10th)"
    INTERMEDIATE = "intermediate", "Intermediate (12th / Diploma)"
    DEGREE = "degree", "Degree / B.Tech"
    POST_GRADUATION = "post_graduation", "Post Graduation"


class EducationBoard(models.TextChoices):
    CBSE = "cbse", "CBSE"
    ICSE = "icse", "ICSE"
    STATE_BOARD = "state_board", "State Board"
    OTHER = "other", "Others"


class IntermediateStream(models.TextChoices):
    MPC = "mpc", "MPC"
    BIPC = "bipc", "BiPC"
    MEC = "mec", "MEC"
    CEC = "cec", "CEC"
    DIPLOMA = "diploma", "Diploma"
    OTHER = "other", "Others"


class DegreeType(models.TextChoices):
    BTECH = "btech", "B.Tech"
    BE = "be", "B.E"
    BSC = "bsc", "B.Sc"
    BCOM = "bcom", "B.Com"
    BBA = "bba", "BBA"
    BA = "ba", "BA"
    BCA = "bca", "BCA"
    MCA_INTEGRATED = "mca_integrated", "MCA Integrated"
    OTHER = "other", "Others"


class PGDegreeType(models.TextChoices):
    MTECH = "mtech", "M.Tech"
    ME = "me", "M.E"
    MBA = "mba", "MBA"
    MSC = "msc", "M.Sc"
    MCOM = "mcom", "M.Com"
    MA = "ma", "MA"
    MCA = "mca", "MCA"
    PHD = "phd", "PhD"
    OTHER = "other", "Others"


class EducationScoreType(models.TextChoices):
    PERCENTAGE = "percentage", "Percentage"
    CGPA = "cgpa", "CGPA"


EDUCATION_LEVEL_ORDER = {
    EducationLevel.SCHOOL: 0,
    EducationLevel.INTERMEDIATE: 1,
    EducationLevel.DEGREE: 2,
    EducationLevel.POST_GRADUATION: 3,
}
