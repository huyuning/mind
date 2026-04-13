#!/usr/bin/env python3
"""
========================================================
全连接图主线纠缠共振稳定码实验
========================================================

纯共振实验（基于全连接图主线）：
1. 生成随机正确码
2. 随机注入一个错误
3. 共振扫描：翻转错误位和纠缠位
4. 重复扫描直到稳定
5. 观测稳定后的码
"""

import numpy as np
from datetime import datetime

class ResonanceStable:
    def __init__(self):
        # 7位码，纠缠映射
        # 位置:     0  1  2  3  4  5  6
        #           D0 P0 P1 D1 P2 D2 D3
        self.entanglement = {
            0: [1],       # D0 ↔ P0
            1: [0, 3, 6], # P0 ↔ D0, D1, D3
            2: [0, 5, 6], # P1 ↔ D0, D2, D3
            3: [1, 4],    # D1 ↔ P0, P2
            4: [3, 5],    # P2 ↔ D1, D2
            5: [2, 4],    # D2 ↔ P1, P2
            6: [1, 2],    # D3 ↔ P0, P1
        }

        np.random.seed(int(datetime.now().timestamp()) % 100000)

        print("=" * 60)
        print("  全连接图主线纠缠共振稳定码实验")
        print("=" * 60)
        print(f"纠缠映射: {self.entanglement}")

    def generate_correct_code(self):
        """生成随机正确码"""
        return [np.random.randint(0, 2) for _ in range(7)]

    def inject_error(self, code):
        """注入一个错误"""
        err_code = code.copy()
        pos = np.random.randint(0, 7)
        err_code[pos] ^= 1
        return err_code, pos

    def resonance_flip(self, code, error_pos):
        """共振翻转：错误位和纠缠位一起翻转"""
        new_code = code.copy()
        entangled = self.entanglement.get(error_pos, [])

        new_code[error_pos] ^= 1
        for pos in entangled:
            new_code[pos] ^= 1

        return new_code, [error_pos] + entangled

    def scan_until_stable(self, code, error_pos, max_iter=100):
        """共振扫描直到稳定"""
        current = code.copy()
        iterations = 0
        history = [current]

        for _ in range(max_iter):
            after_flip, flipped = self.resonance_flip(current, error_pos)

            if after_flip == current:
                break

            if after_flip in history:
                break

            current = after_flip
            history.append(current)
            iterations += 1

        return current, iterations, len(history)

    def run_trial(self):
        """单次试验"""
        original = self.generate_correct_code()
        with_error, error_pos = self.inject_error(original)

        stable, iterations, total_states = self.scan_until_stable(with_error, error_pos)

        back_to_original = (stable == original)

        return {
            'original': original,
            'error_pos': error_pos,
            'with_error': with_error,
            'stable': stable,
            'iterations': iterations,
            'total_states': total_states,
            'back_to_original': back_to_original,
        }

    def run(self, n=100):
        print(f"\n运行 {n} 次试验...")
        results = []
        for i in range(n):
            results.append(self.run_trial())
            if (i + 1) % 20 == 0:
                print(f"  进度: {i+1}/{n}")
        return results

    def analyze(self, results):
        total = len(results)
        n_back = sum(1 for r in results if r['back_to_original'])
        avg_iter = np.mean([r['iterations'] for r in results])
        avg_states = np.mean([r['total_states'] for r in results])

        print(f"\n{'='*60}")
        print("  实验结果分析")
        print(f"{'='*60}")
        print(f"\n总实验: {total}")
        print(f"回到原始码: {n_back}/{total} = {n_back/total*100:.1f}%")
        print(f"进入新稳态: {total-n_back}/{total} = {(total-n_back)/total*100:.1f}%")
        print(f"平均迭代次数: {avg_iter:.1f}")
        print(f"平均状态数: {avg_states:.1f}")

        return {'total': total, 'n_back': n_back, 'avg_iter': avg_iter}

    def show_examples(self, results, n=8):
        print(f"\n{'='*60}")
        print("  典型例子")
        print(f"{'='*60}")
        for i, r in enumerate(results[:n]):
            print(f"\n例子{i+1}:")
            print(f"  原始码:   {r['original']}")
            print(f"  错误位:   {r['error_pos']}")
            print(f"  错误码:   {r['with_error']}")
            print(f"  稳定码:   {r['stable']}")
            print(f"  迭代:     {r['iterations']}, 状态数: {r['total_states']}")
            print(f"  结果:     {'回到原始' if r['back_to_original'] else '新稳态'}")


def main():
    exp = ResonanceStable()
    results = exp.run(n=100)
    exp.show_examples(results, n=8)
    a = exp.analyze(results)

    print(f"\n{'='*60}")
    print("  结论")
    print(f"{'='*60}")
    if a['n_back'] == 0:
        print("共振扫描从不回到原始码")
        print("系统进入新稳态，而非纠正错误")


if __name__ == "__main__":
    main()
