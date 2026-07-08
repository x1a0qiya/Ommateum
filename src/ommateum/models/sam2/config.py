import torch
from peft import LoraConfig, prepare_model_for_kbit_training, get_peft_model, PeftModel, PeftMixedModel
from transformers import Sam2Model, BitsAndBytesConfig

def add_lora_config(
    model_path : str,
    use_quant : bool = False,
    lora_rank : int = 8,
    use_dora : bool = True,
    attention : str = 'sdpa',
    train_prompt : bool = True
) -> PeftModel | PeftMixedModel:
    """
    在 SAM2 模型中添加 LoRA

    Args:
        model_path (str) : SAM2 在本地或者 Hugging Face 中的地址
        use_quant (bool) : 是否启用 4-bit 量化, 启用后将使用 QLoRA 加载模型, 能节省显存
        lora_rank (int) : LoRA 的秩
        use_dora (bool) : 是否使用 dora
        attention (str) : 选用的注意力机制, 默认为 sdpa (缩放点积注意力)
        train_prompt (bool) : 是否同步训练 SAM2 的 Prompt Encoder
    
    Returns:
        PeftModel | PeftMixedModel : 加载好 LoRA 的 SAM2 模型
    """
    quant_config = BitsAndBytesConfig(
        load_in_4bit=use_quant,
        bnb_4bit_quant_type='nf4',
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16
    )

    if use_quant:
        model = Sam2Model.from_pretrained(
            model_path,
            quantization_config=quant_config,
            ignore_mismatched_sizes=True,
            attn_implementation=attention,
            low_cpu_mem_usage=True
        )
        model = prepare_model_for_kbit_training(model)
    else:
        model = Sam2Model.from_pretrained(
            model_path,
            attn_implementation=attention
        )
        model.train()

    lora_alpha = lora_rank * 2
    lora_config = LoraConfig(
        # task_type='mask-generation',
        r=lora_rank,
        lora_alpha=lora_alpha,
        target_modules=['q_proj', 'v_proj', "k_proj", "out_proj"],
        use_dora=use_dora
    )
    model = get_peft_model(model, lora_config)

    if train_prompt:
        for name, para in model.named_parameters():
            if 'prompt_encoder' in name:
                para.requires_grad = True

    model.enable_input_require_grads()

    return model