#!/usr/bin/env python3
"""
========================================================
标准(7,4)汉明码纠缠实验 - 1000次验证
========================================================
"""

import numpy as np
from datetime import datetime

class StandardHamming:
    def __init__(self):
        self.data_pos = [0, 1, 2, 3]
        self.parity_pos = [4, 5, 6]

        self.entanglement = {
            0: [4, 5],
            1: [4, 6],
            2: [4, 5, 6],
            3: [5, 6],
        }

        np.random.seed(int(datetime.now().timestamp()) % 100000)

        print("=" * 60)
        print("  标准(7,4)汉明码纠缠实验")
        print("=" * 60)

    def encode(self, data):
        code = [0] * 7
        for i, d in enumerate(data):
            code[i] = d
        code[4] = code[0] ^ code[1] ^ code[2]
        code[5] = code[0] ^ code[2] ^ code[3]
        code[6] = code[1] ^ code[2] ^ code[3]
        return code

    def inject_error(self, code):
        err_code = code.copy()
        pos = np.random.randint(0, 7)
        err_code[pos] ^= 1
        return err_code, pos

    def resonance_flip(self, code, error_pos):
        new_code = code.copy()
        entangled = self.entanglement.get(error_pos, [])
        for pos in entangled:
            new_code[pos] ^= 1
        return new_code, entangled

    def run_trial(self):
        data = [np.random.randint(0, 2) for _ in range(4)]
        original = self.encode(data)
        with_error, error_pos = self.inject_error(original)
        flipped, entangled = self.resonance_flip(with_error, error_pos)

        return {
            'original': original,
            'error_pos': error_pos,
            'with_error': with_error,
            'flipped': flipped,
            'entangled': entangled,
            'back': flipped == original,
        }

    def run(self, n=1000):
        print(f"运行 {n} 次试验...")
        results = []
        for i in range(n):
            results.append(self.run_trial())
            if (i + 1) % 200 == 0:
                print(f"  进度: {i+1}/{n}")
        return results

    def analyze(self, results):
        total = len(results)
        n_back = sum(1 for r in results if r['back'])
        n_new = total - n_back

        print(f"\n{'='*60}")
        print("  实验结果分析 (1000次)")
        print(f"{'='*60}")

        print(f"\n基本统计:")
        print(f"  总实验: {total}")
        print(f"  回到正确: {n_back}/{total} = {n_back/total*100:.1f}%")
        print(f"  新稳态: {n_new}/{total} = {n_new/total*100:.1f}%")

        print(f"\n各位置统计:")
        pos_stats = {i: {'total': 0, 'back': 0, 'has_ent': 0} for i in range(7)}
        for r in results:
            ep = r['error_pos']
            pos_stats[ep]['total'] += 1
            if r['back']:
                pos_stats[ep]['back'] += 1
            if r['entangled']:
                pos_stats[ep]['has_ent'] += 1

        for pos in range(7):
            s = pos_stats[pos]
            ent_rate = s['has_ent'] / s['total'] * 100 if s['total'] > 0 else 0
            print(f"  位置{pos}: {s['total']}次, 回到正确{s['back']}次, 有纠缠{s['has_ent']}次({ent_rate:.0f}%)")

        ent_counts = {i: 0 for i in range(7)}
        for r in results:
            for pos in r['entangled']:
                ent_counts[pos] += 1

        print(f"\n各位置被翻转次数:")
        for pos, count in sorted(ent_counts.items()):
            print(f"  位置{pos}: {count}次 ({count/total*100:.1f}%)")

        return {'total': total, 'back': n_back, 'new': n_new}


def main():
    exp = StandardHamming()
    results = exp.run(n=1000)
    analysis = exp.analyze(results)

    print(f"\n{'='*60}")
    print("  结论")
    print(f"{'='*60}")
    print(f"进入新稳态: {analysis['new']/analysis['total']*100:.1f}%")

    if analysis['new'] / analysis['total'] > 0.8:
        print("\n✓ 验证：纠缠翻转导致系统进入新稳态")


if __name__ == "__main__":
    main()