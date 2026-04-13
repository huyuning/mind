#!/usr/bin/env python3
"""
========================================================
纠缠共振多次迭代实验
========================================================

实验：持续迭代共振扫描，观察长期行为
"""

import numpy as np
from datetime import datetime

class ResonanceMultiIter:
    def __init__(self):
        self.entanglement = {
            0: [1],
            1: [0, 3, 6],
            2: [0, 5, 6],
            3: [1, 4],
            4: [3, 5],
            5: [2, 4],
            6: [1, 2],
        }

        np.random.seed(int(datetime.now().timestamp()) % 100000)

        print("=" * 60)
        print("  纠缠共振多次迭代实验")
        print("=" * 60)

    def generate_correct_code(self):
        return [np.random.randint(0, 2) for _ in range(7)]

    def inject_error(self, code):
        err_code = code.copy()
        pos = np.random.randint(0, 7)
        err_code[pos] ^= 1
        return err_code, pos

    def resonance_flip(self, code, error_pos):
        new_code = code.copy()
        entangled = self.entanglement.get(error_pos, [])
        new_code[error_pos] ^= 1
        for pos in entangled:
            new_code[pos] ^= 1
        return new_code, [error_pos] + entangled

    def run_trial(self, max_iter=20):
        """单次试验，持续迭代"""
        original = self.generate_correct_code()
        current, error_pos = self.inject_error(original)

        history = [current]
        states_seen = {tuple(current): 0}

        for i in range(max_iter):
            after_flip, flipped = self.resonance_flip(current, error_pos)

            if tuple(after_flip) in states_seen:
                return {
                    'original': original,
                    'error_pos': error_pos,
                    'history': history,
                    'final': current,
                    'loop_detected': True,
                    'loop_start': states_seen[tuple(after_flip)],
                    'total_iter': i,
                    'unique_states': len(states_seen),
                    'back_to_original': current == original,
                }

            current = after_flip
            states_seen[tuple(current)] = i + 1
            history.append(current)

        return {
            'original': original,
            'error_pos': error_pos,
            'history': history,
            'final': current,
            'loop_detected': False,
            'total_iter': max_iter,
            'unique_states': len(states_seen),
            'back_to_original': current == original,
        }

    def run(self, n=50, max_iter=50):
        print(f"运行 {n} 次试验，每次最多 {max_iter} 次迭代...")
        results = []
        for i in range(n):
            results.append(self.run_trial(max_iter))
            if (i + 1) % 10 == 0:
                print(f"  进度: {i+1}/{n}")
        return results

    def analyze(self, results):
        total = len(results)
        n_loop = sum(1 for r in results if r['loop_detected'])
        n_back = sum(1 for r in results if r['back_to_original'])
        avg_iter = np.mean([r['total_iter'] for r in results])
        avg_states = np.mean([r['unique_states'] for r in results])

        print(f"\n{'='*60}")
        print("  实验结果分析")
        print(f"{'='*60}")
        print(f"\n总实验: {total}")
        print(f"检测到循环: {n_loop}/{total} = {n_loop/total*100:.1f}%")
        print(f"回到原始码: {n_back}/{total} = {n_back/total*100:.1f}%")
        print(f"平均迭代次数: {avg_iter:.1f}")
        print(f"平均唯一状态数: {avg_states:.1f}")

        # 循环长度分析
        if n_loop > 0:
            loop_lengths = []
            for r in results:
                if r['loop_detected']:
                    loop_len = r['total_iter'] - r['loop_start']
                    loop_lengths.append(loop_len)
            print(f"平均循环长度: {np.mean(loop_lengths):.1f}")

        return {'total': total, 'n_loop': n_loop, 'n_back': n_back}

    def show_examples(self, results, n=6):
        print(f"\n{'='*60}")
        print("  典型例子")
        print(f"{'='*60}")
        for i, r in enumerate(results[:n]):
            print(f"\n例子{i+1}:")
            print(f"  原始码: {r['original']}")
            print(f"  错误位: {r['error_pos']}")
            print(f"  最终码: {r['final']}")
            print(f"  迭代次数: {r['total_iter']}")
            print(f"  唯一状态数: {r['unique_states']}")
            print(f"  循环: {r['loop_detected']}")
            print(f"  回到原始: {r['back_to_original']}")

            if len(r['history']) <= 10:
                print(f"  演变: {' → '.join([str(h) for h in r['history']])}")


def main():
    exp = ResonanceMultiIter()
    results = exp.run(n=30, max_iter=30)
    exp.show_examples(results, n=6)
    a = exp.analyze(results)


if __name__ == "__main__":
    main()