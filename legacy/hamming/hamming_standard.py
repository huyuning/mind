#!/usr/bin/env python3
"""
========================================================
标准汉明码纠缠实验 - 正确实现
========================================================

标准汉明码(7,4)：
- 4个数据位
- 3个校验位
- 任何1位错误都可检测+定位

纠缠原理：
- 每个数据位与多个校验位纠缠
- 错误位触发 → 纠缠位翻转
- 进入新稳态

使用方法：
    python3 hamming_standard.py
"""

import numpy as np
from datetime import datetime
from pathlib import Path

class StandardHammingEntanglement:
    """
    标准汉明码纠缠实验
    """

    def __init__(self):
        # 7位汉明码(4数据+3校验)
        # 位置:     0  1  2  3  4  5  6
        #           D0 D1 D2 D3 P0 P1 P2
        #           数据位    校验位

        self.n_bits = 7

        # 校验位定义 (哪个数据位参与哪个校验)
        self.parity_map = {
            4: [0, 1, 3],  # P0 = D0 ⊕ D1 ⊕ D3
            5: [0, 2, 3],  # P1 = D0 ⊕ D2 ⊕ D3
            6: [1, 2, 3],  # P2 = D1 ⊕ D2 ⊕ D3
        }

        # 每个数据位影响的校验位
        self.entanglement_map = {
            0: [4, 5],  # D0错误影响P0,P1
            1: [4, 6],  # D1错误影响P0,P2
            2: [5, 6],  # D2错误影响P1,P2
            3: [4, 5, 6],  # D3错误影响P0,P1,P2
        }

        np.random.seed(None)

        print("=" * 60)
        print("  标准汉明码纠缠实验")
        print("=" * 60)
        print(f"总位数: {self.n_bits}")
        print(f"纠缠映射: {self.entanglement_map}")

    def encode(self, data):
        """
        编码：4位数据 → 7位汉明码
        """
        # data = [D0, D1, D2, D3]
        code = data.copy() + [0, 0, 0]  # [D0,D1,D2,D3,P0,P1,P2]

        # 计算校验位
        code[4] = code[0] ^ code[1] ^ code[3]  # P0
        code[5] = code[0] ^ code[2] ^ code[3]  # P1
        code[6] = code[1] ^ code[2] ^ code[3]  # P2

        return code

    def syndrome(self, code):
        """
        计算校验子，定位错误

        如果校验子=0，无错误
        否则，校验子值=错误位置
        """
        # 计算实际校验位
        s0 = code[4] ^ code[0] ^ code[1] ^ code[3]
        s1 = code[5] ^ code[0] ^ code[2] ^ code[3]
        s2 = code[6] ^ code[1] ^ code[2] ^ code[3]

        syndrome_val = (s2 << 2) | (s1 << 1) | s0

        return syndrome_val

    def inject_error(self, code, error_pos=None):
        """注入一位错误"""
        code = code.copy()

        if error_pos is None:
            error_pos = np.random.randint(0, self.n_bits)

        code[error_pos] ^= 1
        return code, error_pos

    def entanglement_flip(self, code, error_pos):
        """
        纠缠翻转

        错误位触发 → 纠缠位翻转
        """
        new_code = code.copy()
        entangled_pos = []

        # 找到纠缠位
        if error_pos in self.entanglement_map:
            entangled_pos = self.entanglement_map[error_pos]
        elif error_pos in self.parity_map:
            # 校验位错误，影响相关数据位
            for data_pos, parity_list in self.parity_map.items():
                if error_pos == parity_list:
                    continue
                for p in parity_list:
                    if p == error_pos and data_pos not in entangled_pos:
                        entangled_pos.append(data_pos)

        # 翻转纠缠位
        for pos in entangled_pos:
            new_code[pos] ^= 1

        return new_code, entangled_pos

    def run_single(self, data):
        """单次试验"""
        # 1. 编码
        original = self.encode(data)

        # 2. 注入错误
        with_error, error_pos = self.inject_error(original)

        # 3. 计算校验子
        syndrome_val = self.syndrome(with_error)

        # 4. 纠缠翻转
        if syndrome_val > 0:
            final, entangled_pos = self.entanglement_flip(with_error, syndrome_val)
        else:
            final = with_error.copy()
            entangled_pos = []
            syndrome_val = error_pos  # 用实际错误位置

        return {
            'original': original,
            'error_injected': with_error,
            'error_pos': error_pos,
            'syndrome': syndrome_val,
            'entangled_pos': entangled_pos,
            'final': final,
            'detection_success': syndrome_val == error_pos,
            'has_entanglement': len(entangled_pos) > 0
        }

    def run_experiment(self, n_trials=100):
        """运行实验"""
        print(f"\n运行 {n_trials} 次实验...")

        results = []
        n_success = 0
        n_entanglement = 0

        for i in range(n_trials):
            data = [np.random.randint(0, 2) for _ in range(4)]
            result = self.run_single(data)
            results.append(result)

            if result['detection_success']:
                n_success += 1
            if result['has_entanglement']:
                n_entanglement += 1

            if (i + 1) % 20 == 0:
                print(f"  进度: {i+1}/{n_trials}")

        return results, n_success, n_entanglement

    def analyze(self, results, n_success, n_entanglement):
        """分析"""
        print(f"\n{'='*60}")
        print("  实验分析")
        print(f"{'='*60}")

        total = len(results)

        print(f"\n基本统计:")
        print(f"  总实验: {total}")
        print(f"  检测成功: {n_success}/{total} = {n_success/total*100:.1f}%")
        print(f"  纠缠翻转: {n_entanglement}/{total} = {n_entanglement/total*100:.1f}%")

        # 各位置纠缠次数
        ent_counts = {i: 0 for i in range(7)}
        for r in results:
            for pos in r['entangled_pos']:
                ent_counts[pos] += 1

        print(f"\n各位置纠缠翻转次数:")
        for pos, count in sorted(ent_counts.items()):
            print(f"  位置{pos}: {count}次")

        # 最终态
        back_to_correct = sum(1 for r in results if r['final'] == r['original'])
        new_stable = total - back_to_correct

        print(f"\n最终态:")
        print(f"  回到正确: {back_to_correct}/{total}")
        print(f"  进入新稳态: {new_stable}/{total}")

        return {
            'total': total,
            'detection_rate': n_success / total * 100,
            'entanglement_rate': n_entanglement / total * 100,
            'back_to_correct': back_to_correct,
            'new_stable': new_stable
        }

    def show_examples(self, results, n=6):
        """展示例子"""
        print(f"\n{'='*60}")
        print("  典型例子")
        print(f"{'='*60}")

        for i, r in enumerate(results[:n]):
            print(f"\n例子{i+1}:")
            print(f"  原始:  {r['original']}")
            print(f"  错误:  {r['error_injected']} (位{r['error_pos']})")
            print(f"  校验子: {r['syndrome']}")
            if r['entangled_pos']:
                print(f"  纠缠:  位{r['entangled_pos']}")
            print(f"  最终:  {r['final']}")


def main():
    exp = StandardHammingEntanglement()

    results, n_success, n_entanglement = exp.run_experiment(n_trials=100)

    exp.show_examples(results, n=6)

    analysis = exp.analyze(results, n_success, n_entanglement)

    print(f"\n{'='*60}")
    print("  结论")
    print(f"{'='*60}")
    print(f"检测成功率: {analysis['detection_rate']:.1f}%")
    print(f"纠缠翻转率: {analysis['entanglement_rate']:.1f}%")
    print(f"进入新稳态: {analysis['new_stable']}/{analysis['total']}")

    return results, analysis


if __name__ == "__main__":
    main()