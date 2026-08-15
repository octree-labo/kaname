import { DocumentNewPage } from "@/components/document/DocumentNewPage";
import { salesModule } from "@/lib/documentModules";

export default function Page() {
  return <DocumentNewPage config={salesModule} />;
}
