# React + Vite Playbook

Bu belge, `formen-takip` frontend projesinin (React 19, Vite 8, TypeScript, TanStack Query v5, React Router v7, Tailwind CSS v4) mimari kararlarını içerir.

## State Yönetimi
**Ne:** Asenkron veri yönetimi ve sunucu state'i.
**Neden:** Global state kütüphaneleri (Redux vb.) gereksiz boilerplate yaratır.
**Kural:** Sadece TanStack Query v5 kullanılır. Client-side state için React Context veya basit hook'lar tercih edilir.
**Referans:** `frontend/src/api/hooks/`

## Stil ve Tema
**Ne:** Stil tanımlamaları ve tema yönetimi.
**Neden:** SCSS veya harici kütüphaneler yerine standart, utility-first bir yaklaşım benimsenmiştir.
**Kural:** Tailwind CSS v4 kullanılır. Tema renkleri CSS değişkenleriyle (`index.css`) tanımlanır ve Tailwind üzerinden kullanılır.
**Referans:** `frontend/src/index.css`

## Yönlendirme (Routing)
**Ne:** Uygulama içi sayfa geçişleri.
**Neden:** React Router v7 endüstri standardıdır ve framework bağımsızdır.
**Kural:** React Router v7 kullanılarak `frontend/src/App.tsx` üzerinden yönetilir. Sayfa seviyesi component'ler `pages/` altında bulunur.
**Referans:** `frontend/src/App.tsx`
