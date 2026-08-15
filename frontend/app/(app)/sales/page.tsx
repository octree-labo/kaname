import { DocumentListPage } from "@/components/document/DocumentListPage";
import { salesModule } from "@/lib/documentModules";

export default function Page() {
  return <DocumentListPage config={salesModule} />;
}
