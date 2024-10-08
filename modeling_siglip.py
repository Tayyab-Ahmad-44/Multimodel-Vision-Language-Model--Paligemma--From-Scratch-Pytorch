import torch
import torch.nn as nn
from typing import Tuple

class SiglipVisionConfig:
    def __init__(
        self, 
        hidden_size=768, # Size of the embedding vector of this vision transformer that we are going to encode
        intermediate_size=3072, # Size of the linear layer that we are gonna use in the feed forward network 
        num_hidden_layers=12, # Number of layers of this vision transformer
        num_attention_heads=12, # Number of heads in the multi-head attention mechanism
        num_channels=3, # RGB
        image_size=224, # Paligamma Comes in three different sizes, this is 224x224
        patch_size=16, # Each image is gonna divide into 16 patches, Each will be 16x16
        layer_norm_eps=1e-6,
        attention_dropout=0.0,
        num_image_tokens: int = None, # How many image embedding we will be having for each image
        **kwargs
    ):
        super().__init__()
        self.hidden_size=hidden_size
        self.intermediate_size=intermediate_size 
        self.num_hidden_layers=num_hidden_layers
        self.num_attention_heads=num_attention_heads
        self.num_channels=num_channels
        self.image_size=image_size
        self.patch_size=patch_size
        self.layer_norm_eps=layer_norm_eps
        self.attention_dropout=attention_dropout
        self.num_image_tokens=num_image_tokens
        
class SiglipVisionEmbedddings(nn.Module):
    def __init__(self, config: SiglipVisionConfig):
        super().__init__()
        
        self.config = config
        self.embed_dim = config.hidden_size
        self.image_size = config.image_size
        self.patch_size = config.patch_size
        
        self.patch_embedding = nn.Conv2d( # Actually this is extracting information from patches wherer thers is no interact b/w patches
            in_channels=config.num_channels,
            out_channels=self.embed_dim,
            kernel_size=self.patch_size,
            stride=self.patch_size,
            padding="valid"
        )
        
        self.num_patches = (self.image_size // self.patch_size) ** 2 # it will be 14x14 patch so we need 196 
        self.num_positions = self.num_patches # How many positional enciding do we need so its 196 for single patch.

        self.positional_embedding = nn.Embedding(self.num_positions, self.embed_dim)
        self.register_buffer(
            "position_ids", 
            torch.arange(self.num_positions).expand((1, -1)),
            persistent=False,
        )
        
    def forward(self, pixel_values: torch.FloatTensor) -> torch.Tensor:
        _, _, height, width = pixel_values.shape # (Batch_Size, Channels, Height, Width)

        # (Batch_Size, Channels, Height, Width) -> (Batch_Size, Embed_Dim, Num_Patches_H, Num_Patches_W)
        patch_embeds = self.patch_embedding(pixel_values) 

        # (Batch_Size, Embed_Dim, Num_Patches_H, Num_Patches_W) -> (Batch_Size, Embed_Dim, Num_Patches)
        embeddings = patch_embeds.flatten(2)

        # (Batch_Size, Embed_Dim, Num_Patches) -> (Batch_Size, Num_Patches, Embed_Dim)
        embeddings = embeddings.transpose(1, 2)

        # Add positional embeddings to each patch. Each positional encoding is a vector of size equal to patch_seze
        embeddings = embeddings + self.positional_embedding(self.position_ids)

        return embeddings
        

class SiglipMLP(nn.Module):
    def __init__(self, config):
        super().__init__()

        self.config = config
        self.fc1 = nn.Linear(config.hidden_size, config.intermediate_size)
        self.fc2 = nn.Linear(config.intermediate_size, config.hidden_size)

    def forward(self, hidden_states: torch.Tensor) -> torch.Tensor:
        # (Batch_Size, Num_Patches, Embed_Dim) -> (Batch_Size, Num_Patches, Intermidiate_Size) 
        hidden_states = self.fc1(hidden_states)
        
        hidden_states = nn.functional.gelu(hidden_states, approximate="tanh")
        
        # (Batch_Size, Num_Patches, Intermidiate_Size) -> (Batch_Size, Num_Patches, Embed_Dim)
        hidden_states = self.fc2(hidden_states)

        return hidden_states

class SiglipAttention(nn.Module):
    def __init__(self, config):
        super().__init__()    

        self.config = config
        self.embed_dim = config.hidden_size
        self.num_heads = config.num_attention_heads
        self.head_dim = self.embed_dim // self.num_heads
        self.scale = self.head_dim**-0.5 # Equivalent to 1 / sqrt(self.head_dim)
        self.dropout = config.attention_dropout
        
        self.k_proj = nn.Linear(self.embed_dim, self.embed_dim)
        self.v_proj = nn.Linear(self.embed_dim, self.embed_dim)
        self.q_proj = nn.Linear(self.embed_dim, self.embed_dim)
        self.out_proj = nn.Linear(self.embed_dim, self.embed_dim)

    def forward(self, hidden_states: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        # (Batch_Size, Num_Patches, Embed_Dim)
        batch_size, seq_len, _ = hidden_states.size()
        
        query_states = self.q_proj(hidden_states)
        
        key_states = self.k_proj(hidden_states)
        
        value_states = self.v_proj(hidden_states)
        
        # (Batch_Size, Num_Patches, Embed_Dim) -> (Batch_Size, Num_Patches, Num_heads, Head_Dim) -> (Batch_Size, Num_Heads, Num_patches, Head_Dim)
        query_states = query_states.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        key_states = key_states.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        value_states = value_states.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        
        # Calculate the attention using the formula Q * K.Transpose / sqrt(n_h). Attention weights: (Batch_size, Num_Heads, Num_Patches, Num_Patches)
        attn_weights = (torch.matmul(query_states, key_states.transpose(2, 3)) * self.scale)

        if attn_weights.size() != (batch_size, self.num_heads, seq_len, seq_len):
            raise ValueError(
                f"Attention weights should be of size {(batch_size, self.num_heads, seq_len, seq_len)} but is"
                f" {attn_weights.size()}"
            )
            
        # Apply the attention weights row-wise:
        attn_weights = nn.functional.softmax(attn_weights, dim=-1, dtype=torch.float32).to(query_states.dtype)   

        # Apply dropout only during training
        attn_weights = nn.functional.dropout(attn_weights, p=self.dropout, training=self.training)

        # Multiply the attention weights with value states. 
        attn_output = torch.matmul(attn_weights, value_states)
            
        if attn_output.size() != (batch_size, self.num_heads, seq_len, self.head_dim):
            raise ValueError(
                f"Attention weights should be of size {(batch_size, self.num_heads, seq_len, self.head_dim)} but is"
                f" {attn_output.size()}"
            )
        
        # (batch_size, self.num_heads, seq_len, self.head_dim) -> (batch_size, seq_len, self.num_heads, self.head_dim)
        attn_output = attn_output.transpose(1, 2).contiguous()
        
        # (batch_size, seq_len, self.num_heads, self.head_dim) -> (Batch_Size, Num_Patches, Embed_Dim)
        attn_output = attn_output.reshape(batch_size, seq_len, self.embed_dim)

        # This will perform mixing of head with each other to about each other e.g [4x1024] @ [1024x1024]. 
        attn_output = self.out_proj(attn_output)
        
        return attn_output, attn_weights

        
class SiglipEncoder(nn.Module):
    def __init__(self, config: SiglipVisionConfig):
        super().__init__()
        
        self.config = config
        self.layers = nn.ModuleList(
            [SiglipEncoderLayer(config) for _ in range(config.num_hidden_layers)]
        )
        
    def forward(self, input_embeds: torch.Tensor) -> torch.Tensor:
        # input_embeds: [Batch_Size, Num_Patches, Embed_Dim]
        hidden_states = input_embeds
        
        for encoder_layer in self.layers:
            hidden_states = encoder_layer(hidden_states)        
        
        return hidden_states


class SiglipEncoderLayer(nn.Module):
    def __init__(self, config: SiglipVisionConfig):
        super().__init__()
        
        self.embed_dim = config.hidden_size
        self.attn = SiglipAttention(config)
        self.layernorm1 = nn.LayerNorm(self.embed_dim, config.layer_norm_eps)
        self.mlp = SiglipMLP(config)
        self.layernorm2 = nn.LayerNorm(self.embed_dim, config.layer_norm_eps)
        
    def forward(self, hidden_states: torch.Tensor) -> torch.Tensor:
        # residual: (Batch_Size, Num_Patches, Embed_Dim)
        residual = hidden_states
        
        # (Batch_Size, Num_Patches, Embed_Dim) -> (Batch_Size, Num_Patches, Embed_Dim)
        hidden_states = self.layernorm1(hidden_states)
        
        # (Batch_Size, Num_Patches, Embed_Dim) -> (Batch_Size, Num_Patches, Embed_Dim)
        hidden_states, _ = self.attn(hidden_states=hidden_states) # We will feed in embeddings and will get contextualized embeddings.
        
        # Skip Connection
        hidden_states = residual + hidden_states
        
        residual = hidden_states
        
        # (Batch_Size, Num_Patches, Embed_Dim) -> (Batch_Size, Num_Patches, Embed_Dim)
        hidden_states = self.layernorm2(hidden_states)
        
        # (Batch_Size, Num_Patches, Embed_Dim) -> (Batch_Size, Num_Patches, Embed_Dim)
        hidden_states = self.mlp(hidden_states)

        # Skip Connection
        hidden_states = residual + hidden_states       

        # (Batch_Size, Num_Patches, Embed_Dim)
        return hidden_states


class SiglipVisionTransformer(nn.Module):       
    def __init__(self, config: SiglipVisionConfig):
        super().__init__()
        
        self.config = config
        embed_dim = config.hidden_size
        
        self.embeddings = SiglipVisionEmbedddings(config) # This will create the patches out of your image by applying convolution then flatten the image and add positional encoding with it
        self.encoder = SiglipEncoder(config) # We will run patches on the list of layers of Transformer. Which will include Multihead attention, then add&norm then feed forward network then another add&norm
        self.post_layernorm = nn.LayerNorm(embed_dim, eps=config.layer_norm_eps) 
        
    def forward(self, pixel_values: torch.Tensor) -> torch.Tensor:
        # pixel_values: image:  (Batch_size, Channels, Height, Width) -> (Batch_size, Num_Patches, Embed_dim)
        hidden_states = self.embeddings(pixel_values)
        
        last_hidden_state = self.encoder(input_embeds=hidden_states)
        
        last_hidden_state = self.post_layernorm(last_hidden_state)

        return last_hidden_state

        
class SiglipVisionModel(nn.Module):
    def __init__(self, config: SiglipVisionConfig):
        super().__init__()
        self.config = config
        self.vision_model = SiglipVisionTransformer(config)
        
    def forward(self, pixel_values) -> tuple:
        # (Batch_Size, Channels, Height, Width) -> (Batch_Size, Num_Patches, Embed_Dim)
        return self.vision_model(pixel_values=pixel_values)
        