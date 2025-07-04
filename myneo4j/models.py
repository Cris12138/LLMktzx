from django.db import models
from accounts.models import UserProfile
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

# Create your models here.
class MyNode(models.Model):
    name = models.CharField(verbose_name='node的name', blank=True, null=True, default='', max_length=100)
    leixing = models.CharField(verbose_name='类型的中文', blank=True, null=True, default='', max_length=100)

    def __str__(self):
        return str(self.name)

    class Meta:
        ordering = ['-id']
        verbose_name = '节点信息'
        verbose_name_plural = verbose_name


class ChatSession(models.Model):
    """对话标题表"""
    title = models.CharField(verbose_name='对话标题', max_length=200, default='新对话')
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name="用户")
    created_at = models.DateTimeField(verbose_name='创建时间', default=timezone.now)
    updated_at = models.DateTimeField(verbose_name='更新时间', auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']
        verbose_name = '对话会话'
        verbose_name_plural = verbose_name


class MyWenda(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    question = models.CharField(verbose_name='问题', blank=True, null=True, default='', max_length=1000)
    anster = models.CharField(verbose_name='答案', blank=True, null=True, default='', max_length=1000)
    chat_session_id = models.IntegerField(verbose_name='对话会话ID', null=True, blank=True, default=None)
    create_time = models.DateTimeField(verbose_name='创建时间', default=timezone.now)
    update_time = models.DateTimeField(verbose_name='更新时间', auto_now=True)

    # 新增：图片相关字段
    image = models.ImageField(
        upload_to='question_images/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name='问题图片'
    )
    has_image = models.BooleanField(default=False, verbose_name='包含图片')

    def __str__(self):
        return str(self.question)

    class Meta:
        ordering = ['-id']
        verbose_name = '问答信息'
        verbose_name_plural = verbose_name

    @property
    def chat_session(self):
        """获取对应的对话会话（非外键方式）"""
        if self.chat_session_id:
            try:
                return ChatSession.objects.get(id=self.chat_session_id)
            except ChatSession.DoesNotExist:
                return None
        return None


class ForumPost(models.Model):
    title = models.CharField("帖子标题", max_length=200)
    content = models.TextField("帖子内容")
    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name="作者")
    created_at = models.DateTimeField("创建时间", default=timezone.now)
    updated_at = models.DateTimeField("更新时间", auto_now=True)
    views = models.PositiveIntegerField("浏览数", default=0)

    class Meta:
        verbose_name = "论坛帖子"
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def likes_count(self):
        """获取点赞数"""
        return self.likes.count()


class PostLike(models.Model):
    """点赞记录表"""
    post = models.ForeignKey(ForumPost, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name="点赞用户")
    created_at = models.DateTimeField("点赞时间", default=timezone.now)

    class Meta:
        verbose_name = "帖子点赞"
        verbose_name_plural = verbose_name
        unique_together = ('post', 'user')  # 确保用户不能重复点赞


class PostReply(models.Model):
    post = models.ForeignKey(ForumPost, on_delete=models.CASCADE, related_name='replies')
    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name="作者")
    content = models.TextField("回复内容")
    created_at = models.DateTimeField("创建时间", default=timezone.now)

    class Meta:
        verbose_name = "帖子回复"
        verbose_name_plural = verbose_name
        ordering = ['created_at']

    def __str__(self):
        return f"回复: {self.post.title}"


class PatientProfile(models.Model):
    """患者基本信息"""
    user = models.OneToOneField(UserProfile, on_delete=models.CASCADE, verbose_name="关联用户")

    # 基本信息
    blood_type = models.CharField("血型", max_length=5, choices=[
        ('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'), ('O+', 'O+'), ('O-', 'O-')
    ], blank=True, null=True)
    height = models.FloatField("身高(cm)", blank=True, null=True,
                               validators=[MinValueValidator(50), MaxValueValidator(250)])
    weight = models.FloatField("体重(kg)", blank=True, null=True,
                               validators=[MinValueValidator(10), MaxValueValidator(300)])
    phone = models.CharField("手机号", max_length=20, blank=True, null=True)

    # 紧急联系人
    emergency_contact_name = models.CharField("紧急联系人姓名", max_length=50, blank=True, null=True)
    emergency_contact_phone = models.CharField("紧急联系人电话", max_length=20, blank=True, null=True)
    emergency_contact_relationship = models.CharField("与紧急联系人关系", max_length=20, blank=True, null=True)

    # 医疗信息
    allergies = models.TextField("过敏信息", blank=True, null=True, help_text="多个过敏源用逗号分隔")
    chronic_diseases = models.TextField("慢性疾病", blank=True, null=True, help_text="多个疾病用逗号分隔")

    created_at = models.DateTimeField("创建时间", default=timezone.now)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    def __str__(self):
        return f"{self.user.username}的病历档案"

    class Meta:
        verbose_name = "患者档案"
        verbose_name_plural = verbose_name


class MedicalRecord(models.Model):
    """就诊记录"""
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='medical_records',
                                verbose_name="患者")

    # 就诊信息
    visit_date = models.DateField("就诊日期")
    hospital = models.CharField("医院名称", max_length=200)
    department = models.CharField("科室", max_length=100)
    doctor = models.CharField("医生姓名", max_length=100)

    # 诊断信息
    chief_complaint = models.TextField("主诉", blank=True, null=True)
    symptoms = models.TextField("症状描述", blank=True, null=True)
    diagnosis = models.TextField("诊断结果")
    treatment_plan = models.TextField("治疗方案", blank=True, null=True)
    follow_up_plan = models.TextField("复查安排", blank=True, null=True)

    # 处方信息
    prescription = models.TextField("处方药物", blank=True, null=True)

    # 其他信息
    notes = models.TextField("备注", blank=True, null=True)

    created_at = models.DateTimeField("创建时间", default=timezone.now)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    def __str__(self):
        return f"{self.visit_date} - {self.hospital} - {self.diagnosis}"

    class Meta:
        ordering = ['-visit_date']
        verbose_name = "就诊记录"
        verbose_name_plural = verbose_name


class Medication(models.Model):
    """用药记录"""
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='medications',
                                verbose_name="患者")
    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.SET_NULL, null=True, blank=True,
                                       verbose_name="关联就诊记录")

    # 药物信息
    drug_name = models.CharField("药物名称", max_length=200)
    dosage = models.CharField("剂量", max_length=100, help_text="如: 5mg, 500mg等")
    frequency = models.CharField("服用频次", max_length=100, help_text="如: 每日1次, 每日3次等")
    route = models.CharField("给药途径", max_length=50, choices=[
        ('oral', '口服'), ('injection', '注射'), ('topical', '外用'),
        ('inhalation', '吸入'), ('other', '其他')
    ], default='oral')

    # 时间信息
    start_date = models.DateField("开始日期")
    end_date = models.DateField("结束日期", blank=True, null=True)

    # 状态信息
    STATUS_CHOICES = [
        ('active', '正在服用'),
        ('completed', '已完成'),
        ('stopped', '已停药'),
        ('paused', '暂停')
    ]
    status = models.CharField("状态", max_length=20, choices=STATUS_CHOICES, default='active')

    # 副作用
    side_effects = models.TextField("副作用", blank=True, null=True)
    effectiveness = models.IntegerField("药效评分", validators=[MinValueValidator(1), MaxValueValidator(5)], blank=True,
                                        null=True)

    notes = models.TextField("备注", blank=True, null=True)

    created_at = models.DateTimeField("创建时间", default=timezone.now)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    def __str__(self):
        return f"{self.drug_name} - {self.dosage}"

    class Meta:
        ordering = ['-start_date']
        verbose_name = "用药记录"
        verbose_name_plural = verbose_name


class LabReport(models.Model):
    """检查报告"""
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='lab_reports',
                                verbose_name="患者")
    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.SET_NULL, null=True, blank=True,
                                       verbose_name="关联就诊记录")

    # 检查信息
    report_type = models.CharField("检查类型", max_length=100, choices=[
        ('blood_routine', '血常规'), ('urine_routine', '尿常规'), ('biochemistry', '血生化'),
        ('imaging', '影像学检查'), ('pathology', '病理检查'), ('microbiology', '微生物检查'),
        ('immunology', '免疫学检查'), ('other', '其他')
    ])
    test_date = models.DateField("检查日期")
    hospital = models.CharField("检查医院", max_length=200)

    # 报告内容
    report_title = models.CharField("报告标题", max_length=200)
    report_content = models.TextField("报告内容", blank=True, null=True)
    conclusion = models.TextField("检查结论", blank=True, null=True)

    # 文件上传
    report_file = models.FileField("报告文件", upload_to='lab_reports/%Y/%m/', blank=True, null=True)

    # 异常指标
    abnormal_indicators = models.TextField("异常指标", blank=True, null=True, help_text="多个指标用逗号分隔")

    # 状态
    status = models.CharField("状态", max_length=20, choices=[
        ('pending', '待检查'), ('completed', '已完成'), ('reviewing', '审核中')
    ], default='completed')

    notes = models.TextField("备注", blank=True, null=True)

    created_at = models.DateTimeField("创建时间", default=timezone.now)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    def __str__(self):
        return f"{self.test_date} - {self.report_type}"

    class Meta:
        ordering = ['-test_date']
        verbose_name = "检查报告"
        verbose_name_plural = verbose_name


class VitalSigns(models.Model):
    """生命体征记录"""
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='vital_signs',
                                verbose_name="患者")

    # 测量时间
    measurement_date = models.DateTimeField("测量时间", default=timezone.now)

    # 生命体征数据
    systolic_pressure = models.IntegerField("收缩压(mmHg)", blank=True, null=True,
                                            validators=[MinValueValidator(50), MaxValueValidator(300)])
    diastolic_pressure = models.IntegerField("舒张压(mmHg)", blank=True, null=True,
                                             validators=[MinValueValidator(30), MaxValueValidator(200)])
    heart_rate = models.IntegerField("心率(次/分)", blank=True, null=True,
                                     validators=[MinValueValidator(30), MaxValueValidator(250)])
    temperature = models.FloatField("体温(℃)", blank=True, null=True,
                                    validators=[MinValueValidator(30.0), MaxValueValidator(45.0)])
    weight = models.FloatField("体重(kg)", blank=True, null=True,
                               validators=[MinValueValidator(10), MaxValueValidator(300)])
    height = models.FloatField("身高(cm)", blank=True, null=True,
                               validators=[MinValueValidator(50), MaxValueValidator(250)])

    # 其他指标
    blood_sugar = models.FloatField("血糖(mmol/L)", blank=True, null=True,
                                    validators=[MinValueValidator(0), MaxValueValidator(50)])
    oxygen_saturation = models.IntegerField("血氧饱和度(%)", blank=True, null=True,
                                            validators=[MinValueValidator(50), MaxValueValidator(100)])

    # 测量方式和地点
    measurement_method = models.CharField("测量方式", max_length=50, choices=[
        ('home', '家庭自测'), ('hospital', '医院测量'), ('clinic', '诊所测量'), ('other', '其他')
    ], default='home')

    notes = models.TextField("备注", blank=True, null=True)

    created_at = models.DateTimeField("创建时间", default=timezone.now)

    def __str__(self):
        return f"{self.measurement_date.strftime('%Y-%m-%d %H:%M')} - 生命体征"

    @property
    def blood_pressure(self):
        """血压显示格式"""
        if self.systolic_pressure and self.diastolic_pressure:
            return f"{self.systolic_pressure}/{self.diastolic_pressure}"
        return None

    class Meta:
        ordering = ['-measurement_date']
        verbose_name = "生命体征"
        verbose_name_plural = verbose_name


class DoctorAccess(models.Model):
    """医生访问权限"""
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='doctor_accesses',
                                verbose_name="患者")

    # 医生信息
    doctor_name = models.CharField("医生姓名", max_length=100)
    doctor_title = models.CharField("医生职称", max_length=50, blank=True, null=True)
    department = models.CharField("科室", max_length=100)
    hospital = models.CharField("医院", max_length=200)
    doctor_license = models.CharField("医师执业证号", max_length=100, blank=True, null=True)

    # 权限设置
    ACCESS_LEVEL_CHOICES = [
        ('full', '完全访问'),
        ('limited', '限制访问'),
        ('read_only', '只读访问')
    ]
    access_level = models.CharField("访问级别", max_length=20, choices=ACCESS_LEVEL_CHOICES, default='limited')

    # 时间限制
    granted_date = models.DateTimeField("授权时间", default=timezone.now)
    expires_date = models.DateTimeField("过期时间", blank=True, null=True)

    # 访问范围
    can_view_records = models.BooleanField("可查看就诊记录", default=True)
    can_view_medications = models.BooleanField("可查看用药记录", default=True)
    can_view_lab_reports = models.BooleanField("可查看检查报告", default=True)
    can_view_vital_signs = models.BooleanField("可查看生命体征", default=True)

    is_active = models.BooleanField("是否激活", default=True)
    notes = models.TextField("备注", blank=True, null=True)

    created_at = models.DateTimeField("创建时间", default=timezone.now)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    def __str__(self):
        return f"{self.doctor_name} - {self.hospital} - {self.access_level}"

    class Meta:
        ordering = ['-granted_date']
        verbose_name = "医生访问权限"
        verbose_name_plural = verbose_name
        unique_together = ('patient', 'doctor_name', 'hospital')  # 避免重复授权