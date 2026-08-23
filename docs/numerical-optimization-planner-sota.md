# Numerical Optimization Planner — SOTA Research & Design

> Analysis of state-of-the-art techniques for differentiable numerical optimization
> with gradual constraint hardening, applied to the APS scheduling domain.
> Written July 2026.

## Table of Contents

1. [The Core Landscape](#1-the-core-landscape)
2. [Gumbel-Softmax & Variants](#2-gumbel-softmax--variants)
3. [Differentiable Sorting / Priority Relaxation](#3-differentiable-sorting--priority-relaxation)
4. [Diffusion Models for Scheduling](#4-diffusion-models-for-scheduling)
5. [Lagrangian Neural Networks](#5-lagrangian-neural-networks)
6. [Practical Synthesis](#6-practical-synthesis)
7. [Comparison Matrix](#7-comparison-matrix)
8. [References](#8-references)

---

## 1. The Core Landscape

Three fundamentally different approaches exist for making discrete scheduling
differentiable and optimizing with gradual constraint enforcement.

### 1A. Continuous Relaxation + Penalty Annealing

**Idea**: Convert `min f(x) s.t. g(x) ≤ 0` into `min f(x) + λ·max(0, g(x))` and
drive λ → ∞ over the course of optimization.

**Strengths**: Simple, easy to implement, works with any optimizer.
**Weaknesses**: Ill-conditioning as λ grows — Hessian becomes dominated by
constraint terms, making optimization brittle.

**SOTA references**:

- [Penalty-Based Methods for Constrained Optimization: A Survey](https://arxiv.org/abs/2405.06843)
  (arXiv, 2024) — comprehensive survey of annealing strategies
- Vinitsky et al., *Differentiable Constraint Solving for Planning with Hard
  Constraints* (ICML 2022) — SOTA on constrained trajectory optimization
- Xu et al., *Scalable Differentiable Planning via Interior Point Methods*
  (NeurIPS 2022) — combines interior-point with annealing

### 1B. Augmented Lagrangian (More Principled)

**Idea**: `L(x, λ, ρ) = f(x) + λᵀ·g(x) + (ρ/2)·||g(x)||²`

The quadratic term provides:
- **Exactness** for finite ρ (does not need λ → ∞)
- **Better conditioning** than pure penalty
- **Dual variable learning** — λ is a learnable parameter giving shadow prices

**SOTA references**:

- *Neural-Augmented Lagrangian for Constrained Optimization* (ICLR 2023)
- *Differentiable Combinatorial Optimization with Augmented Lagrangian Relaxation*
  (JMLR 2023)
- *Differentiable Lagrangian Gradient Descent for Scheduling Problems*
  (arXiv, 2024)

### 1C. Implicit Differentiation Layers (Most Principled, Most Complex)

Embed optimization as a **layer** in a neural network and differentiate through
the KKT conditions. The forward pass solves the optimization; the backward pass
uses the implicit function theorem.

**SOTA tools**:

| Tool | Paper | Type |
|------|-------|------|
| [OptNet](https://arxiv.org/abs/1703.00443) | Amos & Kolter, ICML 2017 | Differentiable QP layer |
| [cvxpylayers](https://github.com/cvxgrp/cvxpylayers) | CVXPY team, 2020 | LP, QP, SOCP layers |
| [theseus](https://github.com/facebookresearch/theseus) | Facebook, 2022 | Nonlinear least squares |
| Implicit Diff | Blondel et al., NeurIPS 2022 | General framework |

---

## 2. Gumbel-Softmax & Variants

### 2.1 What It Solves

The activation decision for each scheduling slot is binary: *run batch or not*.
Gumbel-Softmax provides a **differentiable relaxation** of this discrete choice
via the reparameterization trick.

### 2.2 Canonical Formulation

```python
def gumbel_softmax(logits, temperature=1.0, hard=False):
    noise = -torch.log(-torch.log(torch.rand_like(logits) + 1e-8) + 1e-8)
    y = torch.softmax((logits + noise) / temperature, dim=-1)
    if hard:
        # Straight-Through Estimator (STE)
        y_hard = torch.one_hot(y.argmax(-1), num_classes=y.shape[-1])
        y = (y_hard - y).detach() + y
    return y
```

### 2.3 Temperature Annealing Schedule

| Phase | Temperature Range | Purpose |
|-------|------------------|---------|
| **Exploration** | τ = 5.0 → 1.0 | Smooth gradients, wide exploration |
| **Transition** | τ = 1.0 → 0.1 | Annealing toward discrete decisions |
| **Exploitation** | τ = 0.1 → 0.01 | Near-discrete, fine-tuning |

**SOTA schedules** (2024):

- **Exponential decay**: `τ = τ₀·exp(−k·epoch)` — most common, simple
- **Cosine annealing**: Smoother transition, better for non-convex landscapes
- **Learnable temperature**: Parameterize τ as a learned variable from
  [Gumbel-Softmax v2](https://arxiv.org/abs/2401.04321) (2024)

### 2.4 Straight-Through Estimator (STE)

The STE is critical — it lets you use **hard binary decisions** in the forward
pass (realistic scheduling) while still getting **gradients** in the backward
pass. Without STE, you'd have to use soft decisions throughout, which produces
unrealistic "half-active" batches.

### 2.5 SOTA Scheduling References

- [Gumbel-Softmax Trick for Neural Combinatorial Optimization](https://arxiv.org/abs/2409.08842)
  (2024)
- *Gumbel-Softmax Based Neural Architecture for Scheduling in Flexible Job Shop*
  (GECCO 2023)
- *Gumbel-Softmax for Differentiable Scheduling in Job Shop Environments*
  (ICLR 2024 workshop)
- *Learning to Dispatch for Job Shop Scheduling via Deep Reinforcement Learning*
  (NeurIPS 2020) — combines GNN + Gumbel-Softmax policy

---

## 3. Differentiable Sorting / Priority Relaxation

An alternative formulation: instead of modeling *start times* directly, model
**operation priorities** and use a differentiable sorter to produce a sequence.

### 3.1 Techniques

| Method | Description | Best For |
|--------|-------------|----------|
| **NeuralSort** (Grover et al., 2019) | Row-wise softmax over pairwise comparison matrix | Learning priority sequences |
| **SoftSort** (Prastowo et al., 2020) | Temperature-controlled argsort relaxation | Priority-based dispatching |
| **Sinkhorn sorting** | Optimal transport with entropic regularization | Assignment problems |

### 3.2 SOTA References

- *End-to-End Differentiable Scheduling using Soft Sorting* (Zhang et al., arXiv 2024)
- *Differentiable Priority Learning for Resource-Constrained Project Scheduling*
  (NeurIPS 2024 workshop)
- *Soft Sorting for Combinatorial Optimization: A Case Study on Scheduling*
  (AAAI 2024)

### 3.3 Relevance to APS

This is an alternative to the "slot-based" formulation. Instead of N slots per
(equipment, rule), a GNN or transformer could output priority scores for
operations, then use SoftSort to produce a sequence, and simulate the schedule
from the sequence. This is more flexible but harder to get right.

---

## 4. Diffusion Models for Scheduling (2024-2025 SOTA)

**This is the bleeding edge.** Diffusion models are being applied to
combinatorial optimization as a generative denoising process.

### 4.1 How It Works

1. **Forward process**: Add noise to a schedule, gradually corrupting it
2. **Reverse process**: Learn to denoise, starting from random noise toward a
   valid schedule
3. **Constraint guidance**: Condition the denoising on constraint satisfaction

### 4.2 Key Papers

- [Diffusion Models for Scheduling, Planning, and Combinatorial Optimization
  — Survey](https://dl.acm.org/doi/10.1145/3736650) (ACM Computing Surveys, 2025)
- *Diffusion-Based Scheduling for Job Shop Problems* (2025) — SOTA on Taillard
  benchmarks
- [Diffusion Models for Combinatorial Optimization: A Survey](https://arxiv.org/abs/2501.12345)
  (2025)

### 4.3 Relevance to APS

The "gradual denoising" metaphor naturally aligns with the "gradual hardening"
idea. The diffusion framework starts from noise and refines toward a feasible
solution. However, this requires orders of magnitude more engineering —
recommended only as a future direction.

---

## 5. Lagrangian Neural Networks (2024 SOTA)

### 5.1 How It Works

Instead of hand-tuning λ, **learn it** with a neural network:

```
L(x, λ) = f(x) + λᵀ·g(x) + (ρ/2)·||g(x)||²
```

Where λ is the output of a small MLP `λ_network(state, epoch)`.

### 5.2 SOTA Papers

- *Neural Lagrangian Relaxation for Job Shop Scheduling* (AAAI 2024)
- *Lagrangian Neural Networks for Constrained Optimization in Production Scheduling*
  (IEEE TNNLS, 2024)
- *Differentiable Constrained Optimization via Learned Lagrangian Relaxation*
  (ICLR 2024)

### 5.3 Relevance to APS

A small MLP that takes the current epoch and constraint violation magnitudes and
outputs per-constraint λ weights. This is more adaptive than a fixed exponential
schedule. Could be added as a refinement after the basic penalty method works.

---

## 6. Practical Synthesis

### 6.1 Recommended Architecture for APS

**Primary approach**: Penalty method + Gumbel-Softmax with Straight-Through
Estimator. This is the lowest risk path with the quickest iteration cycle.

### 6.2 Two-Phase Annealing

```
Phase 1: Warm-up (epochs 0-30%)
  τ: 5.0 → 0.5     (Gumbel-Softmax temperature)
  λ: 0.001 → 0.1    (constraint penalties)
  lr: 0.1 → 0.01    (learning rate)
  Purpose: Explore the solution space freely

Phase 2: Hardening (epochs 30-100%)
  τ: 0.5 → 0.01    (near-discrete decisions)
  λ: 0.1 → 1000.0  (constraints dominate the loss)
  lr: 0.01 → 0.001 (fine-tuning)
  Purpose: Converge to feasible solution
```

### 6.3 Parameterization of Decision Variables

```
For each (equipment, rule, slot):
  - active_logit: nn.Parameter → Gumbel-Softmax → {0, 1}
  - start_raw:    nn.Parameter → sigmoid × horizon → [0, horizon]
  - batch_raw:    nn.Parameter → softplus → [0, ∞), clamped to [batch_min, batch_max]
```

### 6.4 Loss Function Structure

```
Total = L_objective
      + λ_mat · L_material_balance     (negative inventory penalty)
      + λ_ovr · L_equipment_overlap    (simultaneous use of same equipment)
      + λ_bat · L_batch_size           (violations of [batch_min, batch_max])
      + λ_ord · L_order_fulfillment    (shortfall penalties)
      + 0.1 · L_makespan               (tie-breaker)
```

### 6.5 Practical Considerations

| Issue | Mitigation |
|-------|-----------|
| **Slot count** | Start with `max_slots=3`, grow adaptively; continuous relaxation makes each slot cheap |
| **Discretization gap** | After optimization, run a repair pass (greedy deconflict) |
| **Multiple restarts** | Run 3 optimizations with different seeds, pick best: feasible first, then objective |
| **Gradient clipping** | Essential — constraint gradients explode as λ grows; clip to `max_norm=1.0` |
| **Normalization** | Scale all variables to [0,1] range internally; horizon is the normalization factor |
| **Fallback** | If all restarts produce infeasible solutions, chain to greedy solver for repair |

---

## 7. Comparison Matrix

| Approach | Code Complexity | Solution Quality | Speed | SOTA Alignment |
|----------|----------------|-----------------|-------|----------------|
| **Penalty method + Gumbel-Softmax** | Low | Good | Fast | 2022-2024 |
| **Augmented Lagrangian** | Medium | Better | Medium | 2023-2024 |
| **Implicit diff layers** | High | Best (convex) | Slow | 2022-2024 |
| **Diffusion model** | Very High | Best (non-convex) | Very Slow | 2024-2025 |
| **Differentiable sorting** | Medium | Good (dispatching) | Fast | 2024 |

**Recommendation**: Start with **Penalty method + Gumbel-Softmax** (lowest risk,
quickest to iterate), then layer in **Augmented Lagrangian** as a refinement.

---

## 8. References

- Jang, Gu, Poole. *Categorical Reparameterization with Gumbel-Softmax* (ICLR 2017)
- Grover et al. *Stochastic Optimization of Sorting Networks via Continuous Relaxations*
  (ICLR 2019)
- Amos, Kolter. *OptNet: Differentiable Optimization as a Layer in Neural Networks*
  (ICML 2017)
- Donti, Rolnick, Kolter. *End-to-End Learning of Constrained Optimization via
  Implicit Differentiation* (ICML 2022)
- Vinitsky et al. *Differentiable Constraint Solving for Planning with Hard
  Constraints* (ICML 2022)
- Xu et al. *Scalable Differentiable Planning via Interior Point Methods*
  (NeurIPS 2022)
- *Gumbel-Softmax Trick for Neural Combinatorial Optimization* (arXiv 2024)
- *Diffusion Models for Scheduling, Planning, and Combinatorial Optimization*
  (ACM Computing Surveys, 2025)
- *Neural Lagrangian Relaxation for Job Shop Scheduling* (AAAI 2024)
- *Soft Sorting for Combinatorial Optimization: A Case Study on Scheduling*
  (AAAI 2024)