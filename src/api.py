from typing import Any, Dict, Optional

import httpx


class GroupFactoryApi:
    def __init__(self, base_url: str, api_key: str, timeout: float = 300):
        self.base_url = base_url.rstrip("/")
        self.headers = {"X-API-Key": api_key}
        self.timeout = timeout

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
    ) -> str:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(
                    method,
                    url,
                    headers=self.headers,
                    json=json,
                    params=params,
                    data=data,
                    files=files,
                )
            except httpx.HTTPError as e:
                return f"API request failed: {e}"

        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            return f"API error {response.status_code}: {detail}"

        try:
            payload = response.json()
        except ValueError:
            return response.text

        return payload.get("message") or str(payload)

    async def create_group(self, name: str, description: str) -> str:
        return await self.request(
            "POST",
            "/api/groups",
            json={"name": name, "description": description},
        )

    async def default_users(self) -> str:
        return await self.request("GET", "/api/admin/default-users")

    async def set_default_users(self, user_ids) -> str:
        return await self.request("PUT", "/api/admin/default-users", json={"user_ids": user_ids})

    async def add_default_users(self, user_ids) -> str:
        return await self.request("POST", "/api/admin/default-users", json={"user_ids": user_ids})

    async def remove_default_users(self, user_ids) -> str:
        return await self.request("DELETE", "/api/admin/default-users", json={"user_ids": user_ids})

    async def add_user(self, username: str) -> str:
        return await self.request("POST", "/api/admin/users", json={"username": username})

    async def list_users(self) -> str:
        return await self.request("GET", "/api/users")

    async def get_user(self, user_id: int) -> str:
        return await self.request("GET", f"/api/users/{user_id}")

    async def delete_user(self, user_id: int) -> str:
        return await self.request("DELETE", f"/api/users/{user_id}")

    async def get_group(self, group_id: str) -> str:
        return await self.request("GET", f"/api/groups/{group_id}")

    async def add_users_to_group(self, group_id: str, user_ids) -> str:
        return await self.request(
            "POST",
            f"/api/groups/{group_id}/users",
            json={"user_ids": user_ids},
        )

    async def get_qr(self, qr_group: str = "default") -> str:
        return await self.request("GET", "/api/admin/qr-backup", params={"qr_group": qr_group})

    async def set_qr(self, qr_data: str, qr_group: str = "default") -> str:
        return await self.request(
            "PUT",
            "/api/admin/qr-backup",
            json={"qr_group": qr_group, "qr_data": qr_data},
        )

    async def set_qr_image(self, qr_group: str, image_bytes: bytes, filename: str, content_type: str) -> str:
        return await self.request(
            "POST",
            "/api/admin/qr-backup/image",
            data={"qr_group": qr_group},
            files={"file": (filename, image_bytes, content_type)},
        )

    async def qr_groups(self, qr_group: str = None) -> str:
        params = {"qr_group": qr_group} if qr_group else None
        return await self.request("GET", "/api/admin/qr-groups", params=params)

    async def assign_qr_group(self, qr_group: str, group_ids) -> str:
        return await self.request(
            "POST",
            f"/api/admin/qr-groups/{qr_group}/assignments",
            json={"group_ids": group_ids},
        )

    async def remove_qr_group_assignments(self, group_ids) -> str:
        return await self.request(
            "DELETE",
            "/api/admin/qr-groups/assignments",
            json={"group_ids": group_ids},
        )

    async def sync_qr(self, qr_group: str = "default") -> str:
        return await self.request("POST", "/api/admin/qr-sync", json={"qr_group": qr_group})
