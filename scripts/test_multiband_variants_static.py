import torch

from model.vitcross_seg_modeling_adaptive_multiband_variants import (
    build_multiband_router,
    ROUTER_MODES,
)

torch.manual_seed(42)

MODES = [
    "shared_spatial",
    "modality_spatial",
    "modality_global",
    "modality_static",
]

print("=" * 90)
print("MULTI-BAND VARIANTS STATIC TEST")
print("=" * 90)

for mode in MODES:

    print()
    print("-" * 90)
    print("MODE:", mode)
    print("-" * 90)

    # Reset seed so comparisons are reproducible.
    torch.manual_seed(42)

    router = (
        build_multiband_router(
            mode
        )
    )

    router.train()

    params = sum(
        p.numel()
        for p in router.parameters()
        if p.requires_grad
    )

    print(
        "parameter_count =",
        params,
    )

    optical = torch.randn(
        2,
        8,
        32,
        32,
        requires_grad=True,
    )

    dsm = torch.randn(
        2,
        8,
        32,
        32,
        requires_grad=True,
    )

    out_o, out_d = router(
        optical,
        dsm,
    )

    err_o = (
        out_o.detach()
        - optical.detach()
    ).abs().max().item()

    err_d = (
        out_d.detach()
        - dsm.detach()
    ).abs().max().item()

    print(
        "identity_optical_maxerr =",
        err_o,
    )

    print(
        "identity_dsm_maxerr     =",
        err_d,
    )

    if err_o != 0.0:
        raise RuntimeError(
            f"{mode}: Optical is not exact identity"
        )

    if err_d != 0.0:
        raise RuntimeError(
            f"{mode}: DSM is not exact identity"
        )

    ow = router.last_optical_weights
    dw = router.last_dsm_weights

    print(
        "optical_weights_shape =",
        tuple(ow.shape),
    )

    print(
        "dsm_weights_shape     =",
        tuple(dw.shape),
    )

    osum_err = (
        ow.sum(dim=1)
        - 1.0
    ).abs().max().item()

    dsum_err = (
        dw.sum(dim=1)
        - 1.0
    ).abs().max().item()

    print(
        "optical_weight_sum_maxerr =",
        osum_err,
    )

    print(
        "dsm_weight_sum_maxerr     =",
        dsum_err,
    )

    if osum_err != 0.0:
        raise RuntimeError(
            f"{mode}: Optical softmax invalid"
        )

    if dsum_err != 0.0:
        raise RuntimeError(
            f"{mode}: DSM softmax invalid"
        )

    # --------------------------------------------------------
    # Gradient test
    # --------------------------------------------------------

    loss = (
        out_o.square().mean()
        + 0.37
        * out_d.square().mean()
        + 0.11
        * (
            out_o
            * out_d
        ).mean()
    )

    loss.backward()

    grads = []

    for name, p in router.named_parameters():
        if (
            p.requires_grad
            and p.grad is not None
        ):
            grads.append(
                (
                    name,
                    float(
                        p.grad
                        .detach()
                        .abs()
                        .max()
                    ),
                )
            )

    print("non-null gradients:")

    for name, g in grads:
        print(
            " ",
            name,
            "=",
            g,
        )

    max_grad = max(
        (
            g
            for _, g in grads
        ),
        default=0.0,
    )

    print(
        "max_router_grad_abs =",
        max_grad,
    )

    if max_grad <= 0.0:
        raise RuntimeError(
            f"{mode}: router receives no gradient"
        )

    # --------------------------------------------------------
    # Mode-specific structural assertions
    # --------------------------------------------------------

    if mode == "shared_spatial":

        shared_err = (
            ow - dw
        ).abs().max().item()

        print(
            "shared_opt_dsm_maxerr =",
            shared_err,
        )

        if shared_err != 0.0:
            raise RuntimeError(
                "shared_spatial does not share weights"
            )

        if ow.shape[-2:] != (
            32,
            32,
        ):
            raise RuntimeError(
                "shared_spatial lost spatial routing"
            )

    elif mode == "modality_spatial":

        if ow.shape[-2:] != (
            32,
            32,
        ):
            raise RuntimeError(
                "modality_spatial lost spatial routing"
            )

    elif mode == "modality_global":

        if ow.shape[-2:] != (
            1,
            1,
        ):
            raise RuntimeError(
                "modality_global is not global"
            )

    elif mode == "modality_static":

        if ow.shape[-2:] != (
            1,
            1,
        ):
            raise RuntimeError(
                "modality_static is not global/static"
            )

        names = [
            n
            for n, _
            in router.named_parameters()
        ]

        if names != [
            "static_logits"
        ]:
            raise RuntimeError(
                "modality_static has unexpected "
                f"trainable params: {names}"
            )

    print(
        f"[PASS] {mode}"
    )


print()
print("=" * 90)
print("ALL MULTI-BAND VARIANT STATIC TESTS: PASS")
print("=" * 90)
