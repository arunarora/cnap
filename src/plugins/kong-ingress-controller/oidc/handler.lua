local http = require("resty.http")
local cjson = require("cjson")

local oidcHandler = {
    PRIORITY = 1000,
    VERSION = "0.0.1",
}

function oidcHandler:access(conf)
    kong.log.debug("oidc access handler called")

    if not ngx.var.http_authorization then
        ngx.log(ngx.ERR, "Authorization Header missing in request")
        return ngx.exit(ngx.HTTP_UNAUTHORIZED)
    end

    -- Validate the access token with the identity provider
    local httpclient = http.new()
    local response, error = httpclient:request_uri(conf.token_validation_url, {
        method = "POST",
        body = "client_id=" .. conf.client_id .. "&client_secret=" .. conf.client_secret .. "&token=" .. ngx.var.http_authorization,
        headers = {
            ["Content-Type"] = "application/x-www-form-urlencoded",
        },
    })

    if not response then
        ngx.log(ngx.ERR, "Token Validation Failed: ", error)
        return ngx.exit(ngx.HTTP_INTERNAL_SERVER_ERROR)
    end

    if response.status ~= 200 then
        ngx.log(ngx.ERR, "Token introspection failed: ", response.status)
        return ngx.exit(ngx.HTTP_UNAUTHORIZED)
    else
        ngx.log(ngx.NOTICE, "Token validation result: ", response.body)
    end

    local token_validation_result = cjson.decode(response.body)

    if not token_validation_result.active then
        ngx.log(ngx.ERR, "Access token not active")
        return ngx.exit(ngx.HTTP_UNAUTHORIZED)
    end

    ngx.req.set_header("X-User-Id", token_validation_result.sub)
    ngx.req.set_header("X-Username", token_validation_result.username)

    ngx.log(ngx.INFO, "Token Successfully Validated")
    httpclient:close()
end

return oidcHandler