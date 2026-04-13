#!/usr/bin/env python3
"""
========================================================
标准(7,4)汉明码 - 纠缠共振纠正实验 v3
========================================================

标准汉明码：
- 位置:     0  1  2  3  4  5  6
-           D0 P0 P1 D1 P2 D2 D3
- 校验位位置: 1, 2, 4 (2^0, 2^1, 2^2)

校验方程（标准）：
- P0(位置1) = D0 ⊕ D1 ⊕ D3
- P1(位置2) = D0 ⊕ D2 ⊕ D3
- P2(位置4) = D1 ⊕ D2 ⊕ D3

实验：
1. 生成正确汉明码
2. 选一个数据位D_i，影响两个校验位P_j,P_k
3. 只翻转P_j和P_k
4. 校验子应该指向D_i
5. 用共振扫描，看结果
"""

import numpy as np
from datetime import datetime

class HammingEntanglementFixV3:
    def __init__(self):
        # 标准(7,4)汉明码位置
        # D0=0, D1=3, D2=5, D3=6
        # P0=1, P1=2, P2=4
        self.data_pos = [0, 3, 5, 6]
        self.parity_pos = [1, 2, 4]

        # 数据位影响的校验位
        # D0(位置0) → P0(位置1)
        # D1(位置3) → P0(位置1), P2(位置4)
        # D2(位置5) → P1(位置2), P2(位置4)
        # D3(位置6) → P1(位置2)
        self.data_to_parity = {
            0: [1],       # D0 → P0
            3: [1, 4],    # D1 → P0, P2
            5: [2, 4],    # D2 → P1, P2
            6: [2],       # D3 → P1
        }

        np.random.seed(int(datetime.now().timestamp()) % 100000)

        print("=" * 60)
        print("  标准(7,4)汉明码 - 纠缠共振纠正实验 v3")
        print("=" * 60)
        print(f"数据位: {self.data_pos}")
        print(f"校验位: {self.parity_pos}")
        print(f"纠缠映射: {self.data_to_parity}")

    def encode(self, data):
        """4位数据编码为7位标准汉明码"""
        D0, D1, D2, D3 = data[0], data[1], data[2], data[3]
        code = [0] * 7
        code[0] = D0        # D0在位置0
        code[3] = D1        # D1在位置3
        code[5] = D2        # D2在位置5
        code[6] = D3        # D3在位置6
        code[1] = D0 ^ D1 ^ D3  # P0
        code[2] = D0 ^ D2 ^ D3  # P1
        code[4] = D1 ^ D2 ^ D3  # P2
        return code

    def syndrome(self, code):
        """计算校验子（标准公式）"""
        s0 = code[1] ^ code[0] ^ code[3] ^ code[6]  # P0 ⊕ D0 ⊕ D1 ⊕ D3
        s1 = code[2] ^ code[0] ^ code[5] ^ code[6]  # P1 ⊕ D0 ⊕ D2 ⊕ D3
        s2 = code[4] ^ code[3] ^ code[5] ^ code[6]  # P2 ⊕ D1 ⊕ D2 ⊕ D3
        return (s2 << 2) | (s1 << 1) | s0

    def resonance_scan(self, code, flip_data_pos, parities):
        """共振扫描：翻转数据位和纠缠的校验位"""
        new_code = code.copy()
        for pos in [flip_data_pos] + parities:
            new_code[pos] ^= 1
        return new_code

    def run_trial(self):
        """单次试验"""
        data = [np.random.randint(0, 2) for _ in range(4)]
        original = self.encode(data)

        flip_data_pos = np.random.choice([0, 3, 5, 6])
        parities = self.data_to_parity[flip_data_pos]

        after_inject = original.copy()
        for p in parities:
            after_inject[p] ^= 1

        syndrome = self.syndrome(after_inject)
        syndrome_points_to_data = (syndrome == flip_data_pos)

        after_scan = self.resonance_scan(after_inject, flip_data_pos, parities)

        data_corrected = (after_scan[flip_data_pos] == original[flip_data_pos])
        parities_kept = all(after_scan[p] == after_inject[p] for p in parities)

        return {
            'data': data,
            'original': original,
            'flip_data_pos': flip_data_pos,
            'parities': parities,
            'after_inject': after_inject,
            'syndrome': syndrome,
            'syndrome_points_to_data': syndrome_points_to_data,
            'after_scan': after_scan,
            'data_corrected': data_corrected,
            'parities_kept': parities_kept,
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
        n_syn = sum(1 for r in results if r['syndrome_points_to_data'])
        n_dat = sum(1 for r in results if r['data_corrected'])
        n_par = sum(1 for r in results if r['parities_kept'])

        print(f"\n{'='*60}")
        print("  实验结果分析")
        print(f"{'='*60}")
        print(f"\n总实验: {total}")
        print(f"校验子指向数据位: {n_syn}/{total} = {n_syn/total*100:.1f}%")
        print(f"数据位被纠正: {n_dat}/{total} = {n_dat/total*100:.1f}%")
        print(f"校验位保持修改后: {n_par}/{total} = {n_par/total*100:.1f}%")

        return {'total': total, 'n_syn': n_syn, 'n_dat': n_dat, 'n_par': n_par}

    def show_examples(self, results, n=6):
        print(f"\n{'='*60}")
        print("  典型例子")
        print(f"{'='*60}")
        for i, r in enumerate(results[:n]):
            print(f"\n例子{i+1}:")
            print(f"  数据:   {r['data']}")
            print(f"  原始码: {r['original']}")
            print(f"  数据位: {r['flip_data_pos']} → 校验位{r['parities']}")
            print(f"  改后码: {r['after_inject']}")
            print(f"  校验子: {r['syndrome']} → 指向{r['syndrome_points_to_data']}")
            print(f"  频扫后: {r['after_scan']}")
            print(f"  数据纠正: {r['data_corrected']}, 校验位保持: {r['parities_kept']}")


def main():
    exp = HammingEntanglementFixV3()
    results = exp.run(n=100)
    exp.show_examples(results, n=6)
    a = exp.analyze(results)


if __name__ == "__main__":
    main()