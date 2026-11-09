# 三个真事：一个 issue 看起来没人做，其实已经有人做了

这是一份**样品**。不是演示数据，是我自己踩过的三次，每次都有链接和证据。

---

## 案例一：PR 开着，issue 也开着

`Sh1n1230/security-checker#477`。issue 是开的，没有评论。

一个只看 issue 状态的人会得出：**没人做，我上。**

`already-taken check Sh1n1230/security-checker#477` 的结果：

```
TAKEN — an open PR is on it: #494 test(cli): cover the budget-overrun warning in _estimate
  [pull open] #494 ...
  [pull open] #523 Add test for _estimate budget-exceeded warning (closes #477)
```

**两条开着的 PR。** 这个 issue 在 GitHub 上看是「开着」，因为它要等 PR 合并才关。

代价：如果不查，我会做一份和 #494 一模一样的活。

## 案例二：PR 已经合了，issue 还开着

`eyalgolan/statecraft-israel#2771`。

```
TAKEN — a merged PR already did it: #2781 docs: mvp-checklist marks #2483 done (Fixes #2771)
```

**已经合了。** issue 还开着，只是没人去关。

代价：不查就是白做一遍，而且是给一个已经满意的需求再做一遍。

## 案例三：没有任何引用，但文件已经改了

`elviskahoro/buridan-ui#313`。

这个案例是我写这个工具的原因。issue 开着、没有 PR、没有评论、GitHub 的 timeline 里**一条引用都没有**。

我改完、写完测试、提了 PR，被维护者关掉了——因为**那个文件几周前被一个从没提过这个 issue 的 commit 改过**。

```
UNSURE — scripts/generate_registry.py changed after the issue was opened (a1819f22 ...)
```

**没有任何元数据能告诉你这件事。** 只能去问一个更笨的问题：这个 issue 点名的文件，在它被创建之后，有没有被动过？

代价：一整个晚上，加一条被关掉的 PR。

---

## 这三件事的共同点

不是「我不够小心」。是**「issue 是开的」这个信号，被当成了「没人做」**。

前两个，GitHub 的接口里有答案，只是没人去读。
第三个，接口里根本**没有**答案。

## 所以工具做两件事

1. 读 timeline，把别人嘴上不说、但接口里记着的引用找出来。
2. 再问一个接口答不上来的问题：**文件动过没有。**

第二个问题会给出 `UNSURE`——不是判决，是一个「去看一眼」的提示。它宁可让我多看一眼，也不让我白干一晚。

---

*这份东西可以用作：工具的介绍页、给团队看的说明、或者一份「为什么我们需要这个」的开场。*
