"""
测试技能分类系统
验证技能能被正确分类为攻击类、状态类、防御类
"""
from data_loader import DataLoader
from core.models import SkillCategory

print("=== 技能分类系统测试 ===\n")

# 加载数据
data_loader = DataLoader()
data_loader.load_all()

# 测试攻击类技能
print("1. 攻击类技能")
attack_skills = [name for name, skill in data_loader.skills.items()
                 if skill.category == SkillCategory.ATTACK]
print(f"   找到 {len(attack_skills)} 个攻击类技能")
if attack_skills:
    print(f"   示例: {', '.join(attack_skills[:5])}")
print()

# 测试状态类技能
print("2. 状态类技能")
status_skills = [name for name, skill in data_loader.skills.items()
                 if skill.category == SkillCategory.STATUS]
print(f"   找到 {len(status_skills)} 个状态类技能")
if status_skills:
    print(f"   示例: {', '.join(status_skills[:5])}")
print()

# 测试防御类技能
print("3. 防御类技能")
defense_skills = [name for name, skill in data_loader.skills.items()
                  if skill.category == SkillCategory.DEFENSE]
print(f"   找到 {len(defense_skills)} 个防御类技能")
if defense_skills:
    print(f"   示例: {', '.join(defense_skills[:5])}")
print()

# 验证应对系统能识别技能类别
print("4. 应对系统测试")
if "猛烈撞击" in data_loader.skills:
    skill = data_loader.skills["猛烈撞击"]
    print(f"   猛烈撞击 - 类别: {skill.category.value}")
    assert skill.category == SkillCategory.ATTACK, "猛烈撞击应该是攻击类"
    print("   [PASS] 攻击类技能识别正确")
print()

print("=" * 50)
print("技能分类系统测试完成！")
print(f"总计: {len(data_loader.skills)} 个技能")
print(f"  - 攻击类: {len(attack_skills)}")
print(f"  - 状态类: {len(status_skills)}")
print(f"  - 防御类: {len(defense_skills)}")
print("=" * 50)
