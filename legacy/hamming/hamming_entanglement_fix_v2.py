#!/usr/bin/env python3
"""
========================================================
标准(7,4)汉明码 - 纠缠共振纠正实验 v2
========================================================

实验设计：
1. 生成随机正确汉明码 [D0,D1,D2,D3,P0,P1,P2]
2. 选一个数据位D_i（比如D0，影响P0,P1）
3. 只翻转两个校验位P0,P1（不改数据位）
4. 此时校验子应该指向D0（因为P0,P1与D0的方程不匹配）
5. 正常汉明码纠正会翻转D0
6. 用固定频扫代替汉明码纠正
7. 观测：数据位D0是否被纠正，校验位P0,P1是否保持翻转后的状态

纠缠理论预测：
- 固定频扫会让系统进入新稳态
- 不会像汉明码那样只纠正数据位
- 而是数据位和校验位一起翻转
"""

import numpy as np
from datetime import datetime

class HammingEntanglementFixV2:
    def __init__(self):
        self.data_pos = [0, 3, 5, 6]
        self.parity_pos = [1, 2, 4]

        # 数据位影响的校验位
        self.data_to_parity = {
            0: [1, 2],   # D0 → P0,P1
            3: [1, 4],   # D1 → P0,P2
            5: [2, 4],   # D2 → P1,P2
            6: [1, 2, 4], # D3 → P0,P1,P2
        }

        np.random.seed(int(datetime.now().timestamp()) % 100000)

        print("=" * 60)
        print("  标准(7,4)汉明码 - 纠缠共振纠正实验 v2")
        print("=" * 60)
        print(f"数据位: {self.data_pos}")
        print(f"校验位: {self.parity_pos}")
        print(f"纠缠映射: {self.data_to_parity}")

    def encode(self, data):
        """4位数据编码为7位标准汉明码"""
        code = [0] * 7
        D0, D1, D2, D3 = data[0], data[1], data[2], data[3]
        code[0] = D0
        code[3] = D1
        code[5] = D2
        code[6] = D3
        code[1] = D0 ^ D1 ^ D3  # P0
        code[2] = D0 ^ D2 ^ D3  # P1
        code[4] = D1 ^ D2 ^ D3  # P2
        return code

    def syndrome(self, code):
        """计算校验子"""
        s0 = code[1] ^ code[0] ^ code[3] ^ code[5]
        s1 = code[2] ^ code[0] ^ code[5] ^ code[6]
        s2 = code[4] ^ code[3] ^ code[5] ^ code[6]
        return (s2 << 2) | (s1 << 1) | s0

    def resonance_scan(self, code, data_pos, parities):
        """
        固定频扫（共振）
        - 只翻转预翻转数据位和纠缠的校验位
        - 这模拟了纠缠同步翻转
        """
        new_code = code.copy()
        entangled = [data_pos] + parities

        for pos in entangled:
            new_code[pos] ^= 1

        return new_code, entangled

    def run_trial(self):
        """单次试验"""
        # 随机4位数据
        data = [np.random.randint(0, 2) for _ in range(4)]

        # 编码得到正确汉明码
        original = self.encode(data)

        # 选择一个数据位
        flip_data_pos = np.random.choice([0, 3, 5])
        parities = self.data_to_parity[flip_data_pos]

        # 只翻转两个校验位（不改数据位）
        # 此时校验子应该指向flip_data_pos
        after_inject = original.copy()
        for p in parities:
            after_inject[p] ^= 1

        # 计算校验子
        syndrome = self.syndrome(after_inject)
        syndrome_points_to_data_pos = (syndrome == flip_data_pos)

        # 用固定频扫代替汉明码纠正
        after_scan, entangled = self.resonance_scan(after_inject, flip_data_pos, parities)

        # 检查结果
        data_corrected = (after_scan[flip_data_pos] == original[flip_data_pos])
        parities_kept_modified = all(after_scan[p] == after_inject[p] for p in parities)

        return {
            'data': data,
            'original': original,
            'flip_data_pos': flip_data_pos,
            'parities': parities,
            'after_inject': after_inject,
            'syndrome': syndrome,
            'syndrome_points_to_data': syndrome_points_to_data_pos,
            'after_scan': after_scan,
            'entangled': entangled,
            'data_corrected': data_corrected,
            'parities_kept_modified': parities_kept_modified,
        }

    def run(self, n=100):
        print(f"运行 {n} 次试验...")
        results = []
        for i in range(n):
            results.append(self.run_trial())
            if (i + 1) % 20 == 0:
                print(f"  进度: {i+1}/{n}")
        return results

    def analyze(self, results):
        total = len(results)

        n_syndrome_correct = sum(1 for r in results if r['syndrome_points_to_data'])
        n_data_corrected = sum(1 for r in results if r['data_corrected'])
        n_parities_kept = sum(1 for r in results if r['parities_kept_modified'])

        print(f"\n{'='*60}")
        print("  实验结果分析")
        print(f"{'='*60}")

        print(f"\n基本统计:")
        print(f"  总实验: {total}")
        print(f"  校验子指向数据位: {n_syndrome_correct}/{total} = {n_syndrome_correct/total*100:.1f}%")
        print(f"  数据位被纠正(回到原值): {n_data_corrected}/{total} = {n_data_corrected/total*100:.1f}%")
        print(f"  校验位保持修改后状态: {n_parities_kept}/{total} = {n_parities_kept/total*100:.1f}%")

        return {
            'total': total,
            'syndrome_correct': n_syndrome_correct,
            'data_corrected': n_data_corrected,
            'parities_kept': n_parities_kept,
        }

    def show_examples(self, results, n=6):
        print(f"\n{'='*60}")
        print("  典型例子")
        print(f"{'='*60}")

        for i, r in enumerate(results[:n]):
            print(f"\n例子{i+1}:")
            print(f"  数据:   {r['data']}")
            print(f"  原始码: {r['original']}")
            print(f"  数据位: {r['flip_data_pos']} → 校验位{r['parities']}")
            print(f"  改后码: {r['after_inject']} (只改校验位)")
            print(f"  校验子: {r['syndrome']} → 指向数据位{r['syndrome_points_to_data']}")
            print(f"  频扫后: {r['after_scan']}")
            print(f"  数据位被纠正: {r['data_corrected']}")
            print(f"  校验位保持: {r['parities_kept_modified']}")


def main():
    exp = HammingEntanglementFixV2()
    results = exp.run(n=100)
    exp.show_examples(results, n=6)
    analysis = exp.analyze(results)

    print(f"\n{'='*60}")
    print("  结论")
    print(f"{'='*60}")
    print(f"校验子指向数据位: {analysis['syndrome_correct']}/{analysis['total']}")
    print(f"数据位被纠正: {analysis['data_corrected']}/{analysis['total']}")
    print(f"校验位保持: {analysis['parities_kept']}/{analysis['total']}")

    if analysis['syndrome_correct'] == 100:
        print("\n✓ 验证：只改校验位，校验子指向对应数据位（汉明码设计正确）")
    if analysis['data_corrected'] == 0:
        print("✓ 验证：纠缠共振不纠正数据位")
    if analysis['parities_kept'] > 0:
        print(f"✓ 验证：部分校验位保持修改后状态（进入新稳态）")


if __name__ == "__main__":
    main()