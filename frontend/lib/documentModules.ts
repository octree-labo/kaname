/**
 * 受注/発注/仕入/売上/入金/支払は「ヘッダ＋明細、上位明細への任意連携」という
 * 共通構造を持つため、汎用コンポーネント(components/document/*)へ渡す設定として
 * まとめて定義する。バックエンドの crud.DocumentCRUD と対になる考え方。
 */

export type LineKind = "product" | "amount";

export interface DocumentModuleConfig {
  key: string;
  label: string;
  apiPath: string;
  noField: string;
  dateField: string;
  dateLabel: string;
  noLabel: string;
  hasStatus: boolean;
  lineKind: LineKind;
  upstreamLineField?: string;
  upstreamLabel?: string;
  /** 「上位伝票から取り込む」で使う /api/open-lines/{kind} の kind */
  openLinesKind?: string;
  /** 取り込み元の伝票の名前（例: 受注） */
  upstreamDocLabel?: string;
}

export const ordersModule: DocumentModuleConfig = {
  key: "orders",
  label: "受注",
  apiPath: "/api/orders",
  noField: "orderNo",
  dateField: "orderDate",
  dateLabel: "受注日",
  noLabel: "受注番号",
  hasStatus: true,
  lineKind: "product",
  upstreamLineField: "quotationLineId",
  upstreamLabel: "見積明細ID（任意）",
  openLinesKind: "quotation",
  upstreamDocLabel: "見積",
};

export const purchaseOrdersModule: DocumentModuleConfig = {
  key: "purchase-orders",
  label: "発注",
  apiPath: "/api/purchase-orders",
  noField: "purchaseOrderNo",
  dateField: "orderDate",
  dateLabel: "発注日",
  noLabel: "発注番号",
  hasStatus: true,
  lineKind: "product",
  upstreamLineField: "orderLineId",
  upstreamLabel: "受注明細ID（任意）",
  openLinesKind: "order_for_purchase",
  upstreamDocLabel: "受注",
};

export const purchasesModule: DocumentModuleConfig = {
  key: "purchases",
  label: "仕入",
  apiPath: "/api/purchases",
  noField: "purchaseNo",
  dateField: "purchaseDate",
  dateLabel: "仕入日",
  noLabel: "仕入番号",
  hasStatus: true,
  lineKind: "product",
  upstreamLineField: "purchaseOrderLineId",
  upstreamLabel: "発注明細ID（任意）",
  openLinesKind: "purchase_order",
  upstreamDocLabel: "発注",
};

export const salesModule: DocumentModuleConfig = {
  key: "sales",
  label: "売上",
  apiPath: "/api/sales",
  noField: "salesNo",
  dateField: "salesDate",
  dateLabel: "売上日",
  noLabel: "売上番号",
  hasStatus: true,
  lineKind: "product",
  upstreamLineField: "orderLineId",
  upstreamLabel: "受注明細ID（任意）",
  openLinesKind: "order_for_sales",
  upstreamDocLabel: "受注",
};

export const receiptsModule: DocumentModuleConfig = {
  key: "receipts",
  label: "入金",
  apiPath: "/api/receipts",
  noField: "receiptNo",
  dateField: "receiptDate",
  dateLabel: "入金日",
  noLabel: "入金番号",
  hasStatus: true,
  lineKind: "amount",
  upstreamLineField: "salesLineId",
  upstreamLabel: "売上明細ID（任意）",
  openLinesKind: "sales",
  upstreamDocLabel: "売上",
};

export const paymentsModule: DocumentModuleConfig = {
  key: "payments",
  label: "支払",
  apiPath: "/api/payments",
  noField: "paymentNo",
  dateField: "paymentDate",
  dateLabel: "支払日",
  noLabel: "支払番号",
  hasStatus: true,
  lineKind: "amount",
  upstreamLineField: "purchaseLineId",
  upstreamLabel: "仕入明細ID（任意）",
  openLinesKind: "purchase",
  upstreamDocLabel: "仕入",
};
