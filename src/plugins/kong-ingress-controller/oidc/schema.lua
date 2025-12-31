local PLUGIN_NAME = "oidc"

local schema = {
    name = PLUGIN_NAME,
    fields= {
        {
            config = {
                type = "record",
                fields = {
                    { client_id = { type = "string", required = true }, },
                    { client_secret = { type = "string", required = true }, },
                    { token_validation_url = { type = "string", required = true, match = "https?://.+"  }, },
                },
            },
        },
    },
}

return schema

