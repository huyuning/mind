#!/usr/bin/env python3
"""
========================================================
标准(7,4)汉明码 - 双校验位错误检测（1000次）
========================================================

理论：
- 校验子 = syndrome[2]syndrome[1]syndrome[0]
- 不是简单的 错误位位置异或
- 因为每个s位是多个方程的综合结果
"""

import numpy as np
from datetime import datetime

class DoubleParityStandard:
    def __init__(self):
        self.data_pos = [0, 3, 5, 6]
        self.parity_pos = [1, 2, 4]

        np.random.seed(int(datetime.now().timestamp()) % 100000)

        print("=" * 60)
        print("  标准(7,4)汉明码 - 双校验位错误检测 (1000次)")
        print("=" * 60)

    def encode(self, data):
        code = [0] * 7
        D0, D1, D2, D3 = data[0], data[1], data[2], data[3]
        code[0] = D0
        code[3] = D1
        code[5] = D2
        code[6] = D3
        code[1] = D0 ^ D1 ^ D3
        code[2] = D0 ^ D2 ^ D3
        code[4] = D1 ^ D2 ^ D3
        return code

    def syndrome(self, code):
        s0 = code[1] ^ code[0] ^ code[3] ^ code[5]
        s1 = code[2] ^ code[0] ^ code[5] ^ code[6]
        s2 = code[4] ^ code[3] ^ code[5] ^ code[6]
        return (s2 << 2) | (s1 << 1) | s0

    def inject_error(self, code):
        err_code = code.copy()
        error_positions = sorted(np.random.choice(self.parity_pos, 2, replace=False).tolist())
        for pos in error_positions:
            err_code[pos] ^= 1
        return err_code, error_positions

    def run(self, n=1000):
        print(f"运行 {n} 次试验...")
        results = []
        for i in range(n):
            data = [np.random.randint(0, 2) for _ in range(4)]
            original = self.encode(data)
            with_error, error_pos = self.inject_error(original)
            syndrome = self.syndrome(with_error)
            results.append({
                'original': original,
                'error_pos': error_pos,
                'syndrome': syndrome,
            })
            if (i + 1) % 200 == 0:
                print(f"  进度: {i+1}/{n}")
        return results

    def analyze(self, results):
        total = len(results)

        print(f"\n{'='*60}")
        print("  实验结果分析")
        print(f"{'='*60}")

        # 校验子分布
        syndrome_counts = {}
        for r in results:
            s = r['syndrome']
            syndrome_counts[s] = syndrome_counts.get(s, 0) + 1

        print(f"\n校验子分布 (共{total}次):")
        for s in sorted(syndrome_counts.keys()):
            pct = syndrome_counts[s] / total * 100
            print(f"  校验子{s} (二进制{s:03b}): {syndrome_counts[s]}次 ({pct:.1f}%)")

        # 期望vs实际
        print(f"\n校验子与错误位组合分析:")
        combo_stats = {}
        for r in results:
            ep = tuple(r['error_pos'])
            combo_stats[ep] = combo_stats.get(ep, {'count': 0, 'syndromes': []})
            combo_stats[ep]['count'] += 1
            combo_stats[ep]['syndromes'].append(r['syndrome'])

        for ep in sorted(combo_stats.keys()):
            stats = combo_stats[ep]
            syndromes = stats['syndromes']
            unique_s = set(syndromes)
            expected_xor = ep[0] ^ ep[1]
            match_count = sum(1 for s in syndromes if s == expected_xor)
            print(f"  错误位{list(ep)}: {stats['count']}次, 期望校验子={expected_xor}, 实际={unique_s}, 匹配={match_count}/{stats['count']}")


def main():
    exp = DoubleParityStandard()
    results = exp.run(n=1000)
    exp.analyze(results)

    print(f"\n{'='*60}")
    print("  结论")
    print(f"{'='*60}")
    print("标准(7,4)汉明码改两个校验位时：")
    print("- 校验子能检测到有错误（不为0）")
    print("- 但校验子的值 ≠ 简单错误位异或")
    print("- 这是因为每个s位是多个校验方程的综合结果")


if __name__ == "__main__":
    main()